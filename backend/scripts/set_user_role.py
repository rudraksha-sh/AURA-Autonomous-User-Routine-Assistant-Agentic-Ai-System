"""Explicitly grant or revoke an account's admin role.

Requires --confirm and AURA_ALLOW_ADMIN_ROLE_CHANGE=YES. This script never
creates users or changes passwords.
"""
import argparse
import os

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.user import User


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("email")
    parser.add_argument("--role", choices=("user", "admin"), default="admin")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    if not args.confirm or os.getenv("AURA_ALLOW_ADMIN_ROLE_CHANGE") != "YES":
        parser.error("Set AURA_ALLOW_ADMIN_ROLE_CHANGE=YES and pass --confirm to change a role")
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == args.email.lower()))
        if user is None:
            parser.error("No account found for that email; register it first")
        user.role = args.role
        db.commit()
        print(f"Updated role for {user.email} to {user.role}.")


if __name__ == "__main__":
    main()
