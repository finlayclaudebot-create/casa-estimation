"""Idempotent dev seed: one organisation + one user.

Runs against the database configured by app.core.config.Settings. Safe to run
multiple times; uses email/name uniqueness to skip existing rows.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as `python scripts/seed_dev.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.db.models import Organisation, User
from app.db.session import get_sessionmaker

DEV_ORG_NAME = "Casa Estimation Dev Org"
DEV_USER_EMAIL = "dev@casa-estimation.local"
DEV_USER_NAME = "Casa Dev"


def seed() -> None:
    factory = get_sessionmaker()
    with factory() as session, session.begin():
        org = session.scalar(select(Organisation).where(Organisation.name == DEV_ORG_NAME))
        if org is None:
            org = Organisation(name=DEV_ORG_NAME)
            session.add(org)
            session.flush()
            print(f"[seed] created organisation {org.id}")
        else:
            print(f"[seed] organisation already exists: {org.id}")

        user = session.scalar(select(User).where(User.email == DEV_USER_EMAIL))
        if user is None:
            user = User(
                organisation_id=org.id,
                email=DEV_USER_EMAIL,
                name=DEV_USER_NAME,
                role="admin",
            )
            session.add(user)
            print(f"[seed] created user {DEV_USER_EMAIL}")
        else:
            print(f"[seed] user already exists: {user.id}")


if __name__ == "__main__":
    seed()
