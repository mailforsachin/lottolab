#!/usr/bin/env python3
"""Safely reset the LottoLab admin password."""

from __future__ import annotations

import getpass
import sys

from backend.database.base import SyncSessionLocal
from backend.models import User
from backend.services.auth_service import get_password_hash


MIN_PASSWORD_LENGTH = 8


def main() -> int:
    """Prompt securely for and update the admin password."""
    session = SyncSessionLocal()

    try:
        admin = (
            session.query(User)
            .filter(User.username == "admin")
            .first()
        )

        if admin is None:
            print("Admin user not found.")
            return 1

        print("Reset LottoLab admin password")
        print("=" * 40)

        password = getpass.getpass(
            "Enter new password: "
        )
        confirm = getpass.getpass(
            "Confirm password: "
        )

        if password != confirm:
            print("Passwords do not match.")
            return 1

        if len(password) < MIN_PASSWORD_LENGTH:
            print(
                "Password must be at least "
                f"{MIN_PASSWORD_LENGTH} characters."
            )
            return 1

        admin.hashed_password = get_password_hash(
            password
        )

        session.commit()

        print("Admin password updated successfully.")
        return 0

    except Exception as exc:
        session.rollback()
        print(
            f"Unable to reset admin password: {exc}"
        )
        return 1

    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
