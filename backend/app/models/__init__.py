"""Import all models for Alembic autogenerate and metadata."""

from app.models.base import Base
from app.models import (
    audit,
    auth_directory,
    compliance,
    infra,
    mfa,
    platform,
    settings,
    solace_intel,
)

__all__ = ["Base", "audit", "auth_directory", "compliance", "infra", "mfa", "platform", "solace_intel"]
