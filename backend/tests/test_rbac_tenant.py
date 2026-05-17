"""RBAC and tenant isolation smoke tests."""

from __future__ import annotations

import unittest
import uuid
from unittest.mock import MagicMock

from app.core.exceptions import SecurityException, SolaceHTTPException
from app.core.permissions import assert_any_permission, get_user_permission_codes, user_has_any_permission
from app.core.tenant_context import (
    enable_system_bypass,
    get_organization_id,
    is_system_bypass,
    reset_system_bypass,
    set_organization_id,
)
from app.models.platform import CoreUser


class TenantContextTests(unittest.TestCase):
    def test_system_bypass_is_explicit(self) -> None:
        self.assertFalse(is_system_bypass())
        token = enable_system_bypass("unit-test")
        try:
            self.assertTrue(is_system_bypass())
        finally:
            reset_system_bypass(token)
        self.assertFalse(is_system_bypass())

    def test_organization_context_roundtrip(self) -> None:
        oid = uuid.uuid4()
        set_organization_id(oid)
        self.assertEqual(get_organization_id(), oid)
        set_organization_id(None)
        self.assertIsNone(get_organization_id())


class RBACPermissionTests(unittest.TestCase):
    def test_admin_has_wildcard(self) -> None:
        db = MagicMock()
        user = CoreUser(id=uuid.uuid4(), is_admin=True, organization_id=uuid.uuid4())
        codes = get_user_permission_codes(db, user)
        self.assertIn("*", codes)
        self.assertTrue(user_has_any_permission(db, user, "users.read"))

    def test_missing_permission_raises_403(self) -> None:
        db = MagicMock()
        db.scalars.return_value.all.return_value = []
        user = CoreUser(id=uuid.uuid4(), is_admin=False, organization_id=uuid.uuid4())
        with self.assertRaises(SolaceHTTPException) as ctx:
            assert_any_permission(db, user, "users.read", ip_address="127.0.0.1")
        self.assertEqual(ctx.exception.status_code, 403)


class TenantScopedModelTests(unittest.TestCase):
    def test_require_organization_context_without_org(self) -> None:
        from app.core.tenant_context import require_organization_context

        set_organization_id(None)
        with self.assertRaises(SecurityException):
            require_organization_context()


if __name__ == "__main__":
    unittest.main()
