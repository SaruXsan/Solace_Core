"""Quick check: how many users exist in the configured database."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import func, select  # noqa: E402

from app.core.database import init_engine, session_scope  # noqa: E402
from app.models.platform import CoreUser  # noqa: E402
from app.services import bootstrap_store  # noqa: E402


def main() -> None:
    bootstrap_store.load_bootstrap()
    url = bootstrap_store.get_db_connection_url()
    if not url:
        print("Database not configured (bootstrap.enc missing?)")
        raise SystemExit(1)
    init_engine(url)
    with session_scope() as db:
        total = db.scalar(
            select(func.count())
            .select_from(CoreUser)
            .where(CoreUser.deleted_at.is_(None))
        )
        directory = db.scalar(
            select(func.count())
            .select_from(CoreUser)
            .where(
                CoreUser.deleted_at.is_(None),
                CoreUser.is_directory_user == True,  # noqa: E712
            )
        )
        sample = db.scalars(
            select(CoreUser.username)
            .where(CoreUser.deleted_at.is_(None))
            .order_by(CoreUser.username)
            .limit(8)
        ).all()
    print(f"total_users={total}")
    print(f"directory_users={directory}")
    print(f"sample_usernames={sample}")


if __name__ == "__main__":
    main()
