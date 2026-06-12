#!/usr/bin/env python3
"""
EgoShield Daemon
Local-first, privacy-preserving cognitive shield
Main entry point for the FastAPI server
"""

import os
import sys
import logging
import argparse
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from egoshield.daemon import __version__, __api_version__
from egoshield.daemon.db.connection import init_db, get_db
from egoshield.daemon.services.analysis import AnalysisService
from egoshield.daemon.services.rules import RulesService
from egoshield.daemon.services.settings import SettingsService
from egoshield.daemon.api.routes import (
    router, health_router, settings_router, 
    rules_router, dashboard_router, set_services, set_start_time
)
from egoshield.daemon.utils.logging import setup_logging, log_event
from egoshield.daemon.utils.project_paths import get_project_root, get_dashboard_path


# Global services
analysis_service: AnalysisService = None
rules_service: RulesService = None
settings_service: SettingsService = None
db = None
_start_time = None


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="EgoShield Daemon")
    parser.add_argument(
        '--port',
        type=int,
        default=8765,
        help='Port to listen on (default: 8765)'
    )
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='Host to bind to (default: 127.0.0.1)'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default=None,
        help='Path to SQLite database'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )
    parser.add_argument(
        '--extension-id',
        type=str,
        default=None,
        help='Allowed browser extension ID'
    )
    parser.add_argument(
        '--dashboard-port',
        type=int,
        default=8766,
        help='Dashboard port (default: 8766)'
    )
    return parser.parse_args()


def create_extension_id_validator(extension_id: str = None):
    """Create a function to validate extension origins"""
    valid_ids = {extension_id} if extension_id else set()
    
    def validate_origin(origin: str) -> bool:
        if not origin:
            return False
        
        # Check for localhost dashboard
        if origin.startswith("http://127.0.0.1:8766") or origin.startswith("http://localhost:8766"):
            return True
        
        # Check for extension origins with valid IDs
        for prefix in ["chrome-extension://", "moz-extension://", "safari-extension://"]:
            if origin.startswith(prefix):
                if not valid_ids:
                    # No specific ID required, allow any extension origin
                    return True
                # Extract extension ID from origin
                ext_id = origin.replace(prefix, "").split("/")[0]
                return ext_id in valid_ids
        
        return False
    
    return validate_origin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global analysis_service, rules_service, settings_service, db, _start_time
    
    # Initialize logging
    logger = setup_logging(__version__)
    
    # Record start time for uptime calculation
    _start_time = __import__('time').time()
    
    # Initialize database
    args = parse_args()
    db = init_db(args.db_path)
    
    # Run migrations
    db.run_migrations()
    
    # Run retention purge
    db.retention_purge()
    
    # Initialize services
    rules_service = RulesService(db)
    settings_service = SettingsService(db)
    analysis_service = AnalysisService(db)
    
    # Set services in routes module
    set_services(analysis_service, rules_service, settings_service, db)
    set_start_time(_start_time)
    
    # Initialize async components
    await analysis_service.initialize()
    
    # Log startup
    ollama_status = analysis_service.llm_arbiter.health_status.value
    log_event(logger, "INFO", "daemon_start", {
        'version': __version__,
        'port': args.port,
        'ollama_status': ollama_status
    })
    
    yield
    
    # Shutdown
    await analysis_service.close()
    db.close()
    
    log_event(logger, "INFO", "daemon_stop", {
        'version': __version__,
        'uptime_seconds': int(__import__('time').time() - _start_time)
    })


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    args = parse_args()
    
    app = FastAPI(
        title="EgoShield Daemon",
        description="Local-first, privacy-preserving cognitive shield",
        version=__version__,
        docs_url=None,  # Disable docs in production
        redoc_url=None,
    )
    
    # Set lifespan handler
    app.router.lifespan_context = lifespan
    
    # Get dashboard path using robust path resolution
    dashboard_path = get_dashboard_path()
    
    # Custom CORS middleware that validates extension origins properly
    @app.middleware("http")
    async def validate_origin_middleware(request, call_next):
        origin = request.headers.get("origin")
        
        # Allow requests without origin (e.g., command line tools)
        if not origin:
            return await call_next(request)
        
        # Validate origin
        args = parse_args()
        validator = create_extension_id_validator(args.extension_id)
        
        if not validator(origin):
            # Log rejected origin
            logger = logging.getLogger("egoshield")
            logger.warning(
                "origin_rejected",
                extra={'event': 'origin_rejected', 'data': {
                    'origin': origin[:100] if origin else None,
                    'endpoint': str(request.url.path)
                }}
            )
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=403,
                content={"error": "Forbidden", "code": "INVALID_ORIGIN"}
            )
        
        return await call_next(request)
    
    # Include routers
    app.include_router(router)
    app.include_router(health_router)
    app.include_router(settings_router)
    app.include_router(rules_router)
    app.include_router(dashboard_router)
    
    # Add exception handlers to app (not router)
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        """Handle HTTP exceptions with proper error codes"""
        error_codes = {
            400: "INVALID_PAYLOAD",
            413: "CONTENT_TOO_LARGE",
            422: "VALIDATION_ERROR",
            429: "RATE_LIMITED",
            503: "SERVICE_UNAVAILABLE"
        }
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "code": error_codes.get(exc.status_code, "UNKNOWN_ERROR")
            },
            headers={
                "X-EgoShield-Daemon": __version__
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """Handle unexpected exceptions"""
        logger = logging.getLogger("egoshield")
        logger.error(
            "unhandled_exception",
            extra={'event': 'unhandled_exception', 'data': {
                'error': str(exc),
                'path': request.url.path
            }}
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "code": "INTERNAL_ERROR"
            },
            headers={
                "X-EgoShield-Daemon": __version__
            }
        )
    
    # Mount dashboard on separate port (handled by separate uvicorn process in production)
    # For development/testing, we serve it at /dashboard
    @app.get("/")
    async def root():
        """Redirect to dashboard"""
        return FileResponse(dashboard_path)
    
    @app.get("/dashboard")
    async def serve_dashboard():
        """Serve the dashboard HTML"""
        return FileResponse(dashboard_path)
    
    @app.get("/favicon.ico")
    async def favicon():
        """Serve favicon"""
        return FileResponse(dashboard_path)  # Dashboard has inline SVG
    
    return app


def check_port_available(port: int, host: str) -> bool:
    """Check if a port is available"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            return True
    except OSError:
        return False


def run_dashboard_server(dashboard_port: int):
    """Run the dashboard server on a separate port"""
    import uvicorn
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    
    dashboard_app = FastAPI(title="EgoShield Dashboard")
    
    # Use robust path resolution for dashboard
    project_root = get_project_root()
    dashboard_html = project_root / "dashboard.html"
    
    # Mount static files (extension directory)
    extensions_dir = project_root / "extension"
    if extensions_dir.exists():
        dashboard_app.mount("/extension", StaticFiles(directory=str(extensions_dir)), name="extension")
    
    @dashboard_app.get("/")
    async def serve_dashboard():
        return FileResponse(dashboard_html)
    
    uvicorn.run(dashboard_app, host="127.0.0.1", port=dashboard_port, log_level="info")


def main():
    """Main entry point"""
    args = parse_args()
    
    # Check if port is available
    if not check_port_available(args.port, args.host):
        print(f"Error: Port {args.port} is already in use", file=sys.stderr)
        sys.exit(1)
    
    # Setup structured logging (this replaces basicConfig)
    logger = setup_logging(__version__)
    logger.setLevel(getattr(logging, args.log_level))
    
    # Create app
    app = create_app()
    
    # Start dashboard server in a separate thread
    import threading
    dashboard_thread = threading.Thread(
        target=run_dashboard_server,
        args=(args.dashboard_port,),
        daemon=True,
        name="dashboard-server"
    )
    dashboard_thread.start()
    
    # Run server
    print(f"EgoShield Daemon v{__version__}")
    print(f"Listening on {args.host}:{args.port}")
    print(f"API: http://{args.host}:{args.port}/api/v2")
    print(f"Health: http://{args.host}:{args.port}/health")
    print(f"Dashboard: http://127.0.0.1:{args.dashboard_port}")
    
    # Log daemon startup
    log_event(logger, "INFO", "main_start", {
        'version': __version__,
        'host': args.host,
        'port': args.port,
        'dashboard_port': args.dashboard_port,
        'log_level': args.log_level
    })
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level=args.log_level.lower(),
        access_log=False,
    )


if __name__ == "__main__":
    main()