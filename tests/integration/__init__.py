"""
EgoShield Integration Tests
Tests for full analysis pipeline and API contract
"""

import pytest
import sqlite3
from pathlib import Path
import tempfile
import json

from egoshield.daemon.db.connection import Database
from egoshield.daemon.db.models import (
    AnalysisRepository, TacticRepository, RulesRepository, SettingsRepository
)
from egoshield.daemon.services.analysis import AnalysisService
from egoshield.daemon.services.rules import RulesService
from egoshield.daemon.services.settings import SettingsService


class TestDatabaseInitialization:
    """Test database initialization and schema"""
    
    def test_creates_database_file(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)
        db.initialize()
        
        assert Path(db_path).exists()
    
    def test_creates_tables(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)
        db.initialize()
        
        with db.get_connection() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [t[0] for t in tables]
            
            assert 'analyses' in table_names
            assert 'tactics' in table_names
            assert 'user_rules' in table_names
            assert 'settings' in table_names
            assert 'schema_meta' in table_names
    
    def test_enables_wal_mode(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)
        db.initialize()
        
        with db.get_connection() as conn:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            assert mode.upper() == 'WAL'
    
    def test_inserts_default_settings(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)
        db.initialize()
        
        settings_repo = SettingsRepository(db)
        retention = settings_repo.get('retention_days')
        
        assert retention == '90'
    
    def test_schema_version(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)
        db.initialize()
        
        version = db.get_schema_version()
        assert version == '2'


class TestAnalysisRepository:
    """Test analysis repository operations"""
    
    def test_create_analysis(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)
        db.initialize()
        
        repo = AnalysisRepository(db)
        
        analysis = repo.create({
            'url_hash': 'abc123def456',
            'domain': 'example.com',
            'content_type': 'page',
            'composite_score': 0.65,
            'severity_band': 'HIGH',
            'tactic_count': 3,
            'partial_result': False,
            'arbiter_tier': 3,
            'retention_days': 90
        })
        
        assert analysis.id is not None
        assert analysis.domain == 'example.com'
        assert analysis.composite_score == 0.65
    
    def test_get_recent_analyses(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)
        db.initialize()
        
        repo = AnalysisRepository(db)
        
        # Create multiple analyses
        for i in range(5):
            repo.create({
                'url_hash': f'hash{i}',
                'domain': f'domain{i}.com',
                'content_type': 'page',
                'composite_score': 0.5,
                'severity_band': 'MEDIUM',
                'tactic_count': 1,
                'partial_result': False,
                'arbiter_tier': None,
                'retention_days': 90
            })
        
        recent = repo.get_recent(limit=3)
        assert len(recent) == 3
    
    def test_count_analyses(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)
        db.initialize()
        
        repo = AnalysisRepository(db)
        
        for i in range(3):
            repo.create({
                'url_hash': f'hash{i}',
                'domain': 'example.com',
                'content_type': 'page',
                'composite_score': 0.5,
                'severity_band': 'MEDIUM',
                'tactic_count': 1,
                'partial_result': False,
                'arbiter_tier': None,
                'retention_days': 90
            })
        
        assert repo.count() == 3


class TestTacticRepository:
    """Test tactic repository operations"""
    
    def test_create_tactic(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)
        db.initialize()
        
        analysis_repo = AnalysisRepository(db)
        tactic_repo = TacticRepository(db)
        
        # Create analysis first
        analysis = analysis_repo.create({
            'url_hash': 'abc123',
            'domain': 'example.com',
            'content_type': 'page',
            'composite_score': 0.7,
            'severity_band': 'HIGH',
            'tactic_count': 1,
            'partial_result': False,
            'arbiter_tier': None,
            'retention_days': 90
        })
        
        # Create tactic
        tactic = tactic_repo.create(analysis.id, {
            'detector_name': 'dark_pattern',
            'tactic_name': 'Fake Urgency',
            'severity': 0.8,
            'evidence_phrases': ['limited time offer', 'act now'],
            'explanation': 'Test explanation'
        })
        
        assert tactic.id is not None
        assert tactic.analysis_id == analysis.id
        assert tactic.tactic_name == 'Fake Urgency'
        assert len(tactic.evidence_phrases) == 2
    
    def test_get_tactics_by_analysis(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)
        db.initialize()
        
        analysis_repo = AnalysisRepository(db)
        tactic_repo = TacticRepository(db)
        
        analysis = analysis_repo.create({
            'url_hash': 'abc123',
            'domain': 'example.com',
            'content_type': 'page',
            'composite_score': 0.7,
            'severity_band': 'HIGH',
            'tactic_count': 2,
            'partial_result': False,
            'arbiter_tier': None,
            'retention_days': 90
        })
        
        tactic_repo.create(analysis.id, {
            'detector_name': 'dark_pattern',
            'tactic_name': 'Fake Urgency',
            'severity': 0.8,
            'evidence_phrases': ['limited time'],
            'explanation': None
        })
        
        tactic_repo.create(analysis.id, {
            'detector_name': 'urgency_inflation',
            'tactic_name': 'Countdown',
            'severity': 0.7,
            'evidence_phrases': ['2 hours left'],
            'explanation': None
        })
        
        tactics = tactic_repo.get_by_analysis(analysis.id)
        assert len(tactics) == 2


class TestRulesRepository:
    """Test rules repository operations"""
    
    def test_create_trusted_domain(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)
        db.initialize()
        
        repo = RulesRepository(db)
        
        rule = repo.create({
            'rule_type': 'trusted_domain',
            'value': 'trusted-site.com',
            'notes': 'Personal site'
        })
        
        assert rule.id is not None
        assert rule.value == 'trusted-site.com'
    
    def test_get_rules_dict(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)
        db.initialize()
        
        repo = RulesRepository(db)
        
        repo.create({
            'rule_type': 'trusted_domain',
            'value': 'trusted.com'
        })
        repo.create({
            'rule_type': 'suppress_tactic',
            'value': 'Pity Appeal'
        })
        
        rules = repo.get_rules_dict()
        
        assert 'trusted.com' in rules['trusted_domains']
        assert 'Pity Appeal' in rules['suppressed_tactics']


class TestRetentionPurge:
    """Test retention purge functionality"""
    
    def test_deletes_expired_analyses(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)
        db.initialize()
        
        analysis_repo = AnalysisRepository(db)
        
        # Create analysis with very short retention (for testing)
        analysis_repo.create({
            'url_hash': 'old_hash',
            'domain': 'old.com',
            'content_type': 'page',
            'composite_score': 0.5,
            'severity_band': 'MEDIUM',
            'tactic_count': 1,
            'partial_result': False,
            'arbiter_tier': None,
            'retention_days': -1  # Already expired
        })
        
        # Purge
        analyses_deleted, metrics_deleted = db.retention_purge()
        
        assert analyses_deleted >= 1


class TestSettingsService:
    """Test settings service"""
    
    def test_get_and_set_setting(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)
        db.initialize()
        
        service = SettingsService(db)
        
        # Use a valid setting key from VALID_SETTINGS
        service.set('max_content_bytes', '100000')
        assert service.get('max_content_bytes') == '100000'
    
    def test_get_int_setting(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)
        db.initialize()
        
        service = SettingsService(db)
        
        assert service.get_int('retention_days') == 90
    
    def test_get_bool_setting(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)
        db.initialize()
        
        service = SettingsService(db)
        
        assert service.get_bool('overlay_enabled') is True
    
    def test_validate_setting_types(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)
        db.initialize()
        
        service = SettingsService(db)
        
        # Valid int
        service.set_int('llm_timeout_ms', 10000)
        assert service.get_int('llm_timeout_ms') == 10000
        
        # Valid float
        service.set_float('llm_threshold', 0.5)
        assert service.get_float('llm_threshold') == 0.5
        
        # Valid bool
        service.set_bool('email_analysis_enabled', True)
        assert service.get_bool('email_analysis_enabled') is True


class TestAnalysisService:
    """Test analysis service"""
    
    @pytest.mark.asyncio
    async def test_analyze_content(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)
        db.initialize()
        
        service = AnalysisService(db)
        await service.initialize()
        
        result = await service.analyze(
            content="Act now! Limited time offer! This deal expires soon!",
            url="https://example.com/page",
            domain="example.com",
            content_type="page"
        )
        
        assert result.analysis_id is not None
        assert result.composite_score >= 0
        assert result.severity_band in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        assert isinstance(result.tactics, list)
    
    @pytest.mark.asyncio
    async def test_analysis_includes_evidence(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        db = Database(db_path)
        db.initialize()
        
        service = AnalysisService(db)
        await service.initialize()
        
        result = await service.analyze(
            content="Hurry! Only 3 items left in stock!",
            url="https://example.com/page",
            domain="example.com",
            content_type="page"
        )
        
        if result.tactics:
            for tactic in result.tactics:
                assert len(tactic['evidence_phrases']) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])