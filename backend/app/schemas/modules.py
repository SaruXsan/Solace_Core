from __future__ import annotations

from pydantic import BaseModel


class ModuleOut(BaseModel):
    id: str
    module_name: str
    display_name: str
    version: str
    description: str | None
    enabled: bool
    is_placeholder: bool
    database_prefix: str | None
    permissions: list[str] = []
    routes: list[str] = []


class ModuleUpdateIn(BaseModel):
    enabled: bool | None = None
    description: str | None = None
