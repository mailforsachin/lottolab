"""Regression tests for Bearer authentication dependency wiring."""

from fastapi.params import Depends
from backend.services.auth_service import get_current_user, oauth2_scheme


def test_get_current_user_uses_oauth2_bearer_dependency():
    """Protected endpoints must read JWT from Authorization: Bearer header."""
    default = get_current_user.__defaults__[0]

    assert isinstance(default, Depends)
    assert default.dependency is oauth2_scheme
