"""Pytest configuration and session fixtures."""

import pytest
from app.db.session import init_db

@pytest.fixture(autouse=True, scope="session")
def setup_test_environment():
    """Ensure database schema is initialized before running tests."""
    init_db()
