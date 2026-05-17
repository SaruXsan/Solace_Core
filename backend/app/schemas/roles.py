from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class PermissionOut(BaseModel):
    id: str
    code: str
    name: str
    module_code: str | None


class RoleOut(BaseModel):
    id: str
    name: str
    code: str
    description: str | None
    requires_mfa: bool
    is_system_role: bool
    permission_ids: list[str] = []


class RoleCreateIn(BaseModel):
    name: str = Field(min_length=1)
    code: str = Field(min_length=1)
    description: str | None = None
    requires_mfa: bool = False
    permission_ids: list[UUID] = []


class RoleUpdateIn(BaseModel):
    name: str | None = None
    description: str | None = None
    requires_mfa: bool | None = None
    permission_ids: list[UUID] | None = None


class RolePermissionsIn(BaseModel):
    permission_ids: list[UUID]
