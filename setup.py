"""
EgoShield Setup Configuration
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="egoshield",
    version="2.0.0",
    author="EgoShield Team",
    author_email="team@egoshield.local",
    description="Local-first, privacy-preserving cognitive shield",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/knarayanareddy/egoshield",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Security",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
    ],
    python_requires=">=3.10",
    install_requires=[
        "fastapi>=0.109.0",
        "uvicorn>=0.27.0",
        "pydantic>=2.5.0",
        "httpx>=0.26.0",
        "keyring>=23.13.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "ruff>=0.1.0",
            "mypy>=1.7.0",
            "bandit>=1.7.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "egoshield-daemon=daemon.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "daemon": ["db/schema.sql"],
    },
)