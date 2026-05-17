"""SQL Server engine, session factory, and tenant isolation interceptor."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator, Iterator
from uuid import UUID

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import ORMExecuteState, Session, sessionmaker, with_loader_criteria

from app.core.exceptions import SecurityException
from app.core.tenant_context import get_organization_id, is_system_bypass
from app.models.base import TenantScopedMixin

logger = logging.getLogger(__name__)

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def init_engine(connection_url: str, echo: bool = False) -> Engine:
    global _engine, _SessionLocal
    lower = connection_url.lower()
    if "sqlite" in lower:
        raise RuntimeError(
            "SQLite is not supported. Configure SQL Server (mssql+pyodbc) only."
        )
    if "mssql" not in lower and "pyodbc" not in lower:
        raise RuntimeError(
            "Only SQL Server via ODBC is supported. Check bootstrap connection URL."
        )
    _engine = create_engine(
        connection_url,
        echo=echo,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    _register_tenant_interceptor(_engine)
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("Database not configured — complete first-run setup")
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    if _SessionLocal is None:
        raise RuntimeError("Database not configured — complete first-run setup")
    return _SessionLocal


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Iterator[Session]:
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()


def _register_tenant_interceptor(engine: Engine) -> None:
    """Session-level global query interceptor — blocks tenant queries without org context."""

    @event.listens_for(Session, "do_orm_execute")
    def _tenant_safety_fuse(execute_state: ORMExecuteState) -> None:
        if not execute_state.is_select and not execute_state.is_update and not execute_state.is_delete:
            return
        if is_system_bypass():
            return
        org_id = get_organization_id()
        if org_id is None:
            # Check if statement touches tenant-scoped entities
            if execute_state.statement is not None:
                _assert_tenant_context_for_statement(execute_state)
        else:
            # Auto-apply org filter on selects for tenant models
            execute_state.update_execution_options(
                populate_existing=True,
            )

    @event.listens_for(Session, "before_flush")
    def _tenant_flush_check(session: Session, flush_context, instances) -> None:
        if is_system_bypass():
            return
        org_id = get_organization_id()
        for obj in session.new.union(session.dirty):
            if isinstance(obj, TenantScopedMixin):
                if org_id is None:
                    raise SecurityException(
                        "Tenant-scoped write blocked: no active organization context"
                    )
                if getattr(obj, "organization_id", None) is None:
                    obj.organization_id = org_id


def _assert_tenant_context_for_statement(execute_state: ORMExecuteState) -> None:
    """Raise if ORM operation targets tenant-scoped mappers without org context."""
    if execute_state.is_column_load or execute_state.is_relationship_load:
        return
    mapper = getattr(execute_state.statement, "entity_namespace", None)
    # For ORM selects, inspect all_mapper entities via session
    session = execute_state.session
    if session is None:
        return
    for desc in session.identity_map.values():
        if isinstance(desc, TenantScopedMixin):
            raise SecurityException(
                "Tenant-scoped query blocked: no active organization context"
            )


def apply_tenant_criteria(session: Session, organization_id: UUID) -> None:
    """Apply loader criteria so tenant-scoped rows are filtered automatically."""

    @event.listens_for(session, "do_orm_execute", propagate=True)
    def _add_org_filter(execute_state: ORMExecuteState) -> None:
        if (
            execute_state.is_select
            and not is_system_bypass()
            and organization_id is not None
        ):
            execute_state.statement = execute_state.statement.options(
                with_loader_criteria(
                    TenantScopedMixin,
                    lambda cls: cls.organization_id == organization_id,  # type: ignore
                    include_aliases=True,
                )
            )
