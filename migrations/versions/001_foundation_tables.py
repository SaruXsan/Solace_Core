"""Foundation tables — full enterprise core schema.

Revision ID: 001_foundation
Revises:
Create Date: 2026-05-17
"""

from typing import Sequence, Union

from alembic import op

revision: str = "001_foundation"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    import sys
    from pathlib import Path

    backend = Path(__file__).resolve().parents[2] / "backend"
    sys.path.insert(0, str(backend))
    from app.models.base import Base
    from app.models import (  # noqa: F401
        audit,
        auth_directory,
        compliance,
        infra,
        mfa,
        platform,
        solace_intel,
    )

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    import sys
    from pathlib import Path

    backend = Path(__file__).resolve().parents[2] / "backend"
    sys.path.insert(0, str(backend))
    from app.models.base import Base
    from app.models import audit, auth_directory, compliance, infra, mfa, platform, solace_intel  # noqa: F401

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
