from fastapi import APIRouter

from app.api.v1 import (
    auth,
    compliance,
    dashboard,
    infra,
    logs,
    memory,
    mfa,
    modules,
    organizations,
    roles,
    settings,
    setup,
    users,
)

api_router = APIRouter()
api_router.include_router(setup.router)
api_router.include_router(auth.router)
api_router.include_router(settings.router)
api_router.include_router(mfa.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(modules.router)
api_router.include_router(compliance.router)
api_router.include_router(dashboard.router)
api_router.include_router(logs.router)
api_router.include_router(organizations.router)
api_router.include_router(memory.router)
api_router.include_router(infra.router)
