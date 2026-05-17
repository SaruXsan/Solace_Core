from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserOut(BaseModel):
    id: str
    username: str
    email: str
    display_name: str
    is_active: bool
    is_admin: bool
    is_service_account: bool
    is_privileged_account: bool
    mfa_enabled: bool
    mfa_method: str | None
    directory_source: str
    is_directory_user: bool
    organization_id: str
    branch_id: str | None
    department_id: str | None
    role_ids: list[str] = []


class UserCreateIn(BaseModel):
    username: str = Field(min_length=3, max_length=128)
    email: EmailStr
    display_name: str = Field(min_length=1)
    password: str | None = Field(default=None, min_length=12)
    organization_id: UUID | None = None
    branch_id: UUID | None = None
    department_id: UUID | None = None
    is_admin: bool = False
    is_service_account: bool = False
    is_privileged_account: bool = False
    mfa_enabled: bool = False
    role_ids: list[UUID] = []


class UserUpdateIn(BaseModel):
    email: EmailStr | None = None
    display_name: str | None = None
    password: str | None = Field(default=None, min_length=12)
    branch_id: UUID | None = None
    department_id: UUID | None = None
    is_active: bool | None = None
    is_admin: bool | None = None
    is_service_account: bool | None = None
    is_privileged_account: bool | None = None
    mfa_enabled: bool | None = None
    role_ids: list[UUID] | None = None
