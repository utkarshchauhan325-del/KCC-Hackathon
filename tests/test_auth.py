"""Unit tests for FloodGuard administrator authentication."""

import pytest
from app.ui.views.login import validate_credentials, AUTHORIZED_ADMINS
from app.config import settings


def test_official_admin_credentials():
    """Verify official Pune municipal admin email authenticates."""
    assert validate_credentials("admin@pune.gov.in", "admin123") is True
    assert validate_credentials("ADMIN@PUNE.GOV.IN", "admin123") is True
    assert validate_credentials(" admin@pune.gov.in ", "admin123") is True


def test_admin_gmail_credentials():
    """Verify admin@gmail.com works as requested."""
    assert validate_credentials("admin@gmail.com", "admin123") is True
    assert validate_credentials("Admin@Gmail.com", "admin123") is True


def test_backup_and_settings_credentials():
    """Verify fallback and settings passwords work."""
    assert validate_credentials("admin@pune.gov.in", "FloodGuard@2026") is True
    assert validate_credentials("floodguard@pune.gov.in", "FloodGuard@2026") is True
    if settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD:
        assert validate_credentials(settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD) is True


def test_invalid_credentials_rejected():
    """Verify invalid emails and incorrect passwords reject."""
    assert validate_credentials("admin@pune.gov.in", "wrong_password") is False
    assert validate_credentials("hacker@unknown.com", "admin123") is False
    assert validate_credentials("", "") is False
    assert validate_credentials("admin@pune.gov.in", "") is False
    assert validate_credentials("random@gmail.com", "admin123") is False
