"""Phase 2A security unit tests."""

from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from app.core.permissions import get_user_permission_codes
from app.models.platform import CoreUser
from app.services import mfa_service


class Phase2APermissionTests(unittest.TestCase):
    def test_admin_with_roles_does_not_auto_wildcard(self) -> None:
        """When admin has role permissions, wildcard is not used."""
        db = MagicMock()
        user = CoreUser(id=uuid.uuid4(), is_admin=True, organization_id=uuid.uuid4())

        def scalars_side_effect(stmt):
            result = MagicMock()
            if "Core_UserRole" in str(stmt):
                result.all.return_value = [uuid.uuid4()]
            elif "Core_RolePermission" in str(stmt):
                result.all.return_value = [uuid.uuid4()]
            elif "Core_Permission" in str(stmt):
                result.all.return_value = ["dashboard.read"]
            else:
                result.all.return_value = []
            return result

        db.scalars.side_effect = scalars_side_effect
        codes = get_user_permission_codes(db, user)
        self.assertNotIn("*", codes)
        self.assertIn("dashboard.read", codes)

    def test_admin_without_roles_break_glass_wildcard(self) -> None:
        db = MagicMock()
        db.scalars.return_value.all.return_value = []
        user = CoreUser(id=uuid.uuid4(), is_admin=True, organization_id=uuid.uuid4())
        codes = get_user_permission_codes(db, user)
        self.assertEqual(codes, {"*"})


class Phase2AMfaTests(unittest.TestCase):
    def test_mfa_disabled_until_skips_requirement(self) -> None:
        db = MagicMock()
        user = CoreUser(
            id=uuid.uuid4(),
            is_admin=True,
            mfa_enabled=True,
            mfa_disabled_until=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        self.assertFalse(mfa_service.user_requires_mfa(db, user))


if __name__ == "__main__":
    unittest.main()
