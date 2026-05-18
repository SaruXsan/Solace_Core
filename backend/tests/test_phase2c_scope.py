"""Phase 2C enterprise scope and isolation tests."""

from __future__ import annotations

import unittest
import uuid
from unittest.mock import MagicMock

from app.core.exceptions import SolaceHTTPException
from app.core.scope_context import ActiveScope
from app.core.tenant_context import enable_system_bypass, reset_system_bypass
from app.models.platform import CoreUser, CoreUserRole, CoreUserScope
from app.services import scope_service
from app.services.scope_service import SCOPE_GLOBAL, SCOPE_ORGANIZATION


class ScopeAccessTests(unittest.TestCase):
    def test_user_can_access_assigned_organization(self) -> None:
        db = MagicMock()
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()
        scope = CoreUserScope(
            id=uuid.uuid4(),
            user_id=user_id,
            scope_type=SCOPE_ORGANIZATION,
            organization_id=org_id,
            is_active=True,
        )
        db.scalars.return_value.all.return_value = [scope]
        requested = ActiveScope(
            scope_type=SCOPE_ORGANIZATION,
            country_id=None,
            organization_id=org_id,
            branch_id=None,
            department_id=None,
        )
        self.assertTrue(scope_service.user_can_use_scope(db, user_id, requested))

    def test_user_cannot_access_unassigned_organization(self) -> None:
        db = MagicMock()
        user_id = uuid.uuid4()
        scope = CoreUserScope(
            id=uuid.uuid4(),
            user_id=user_id,
            scope_type=SCOPE_ORGANIZATION,
            organization_id=uuid.uuid4(),
            is_active=True,
        )
        db.scalars.return_value.all.return_value = [scope]
        requested = ActiveScope(
            scope_type=SCOPE_ORGANIZATION,
            country_id=None,
            organization_id=uuid.uuid4(),
            branch_id=None,
            department_id=None,
        )
        self.assertFalse(scope_service.user_can_use_scope(db, user_id, requested))


class ScopedRoleTests(unittest.TestCase):
    def test_global_role_always_applies(self) -> None:
        from app.core.permissions import _role_applies_to_active_scope

        ur = CoreUserRole(
            user_id=uuid.uuid4(),
            role_id=uuid.uuid4(),
            scope_type=SCOPE_GLOBAL,
        )
        active = ActiveScope(SCOPE_ORGANIZATION, None, uuid.uuid4(), None, None)
        self.assertTrue(_role_applies_to_active_scope(ur, active))

    def test_org_role_only_in_matching_company(self) -> None:
        from app.core.permissions import _role_applies_to_active_scope

        org_id = uuid.uuid4()
        ur = CoreUserRole(
            user_id=uuid.uuid4(),
            role_id=uuid.uuid4(),
            scope_type=SCOPE_ORGANIZATION,
            organization_id=org_id,
        )
        match = ActiveScope(SCOPE_ORGANIZATION, None, org_id, None, None)
        other = ActiveScope(SCOPE_ORGANIZATION, None, uuid.uuid4(), None, None)
        self.assertTrue(_role_applies_to_active_scope(ur, match))
        self.assertFalse(_role_applies_to_active_scope(ur, other))


class SwitchScopeTests(unittest.TestCase):
    def test_switch_rejects_unauthorized(self) -> None:
        db = MagicMock()
        user = CoreUser(id=uuid.uuid4(), organization_id=uuid.uuid4(), username="u")
        session = MagicMock()
        db.scalars.return_value.all.return_value = []
        db.scalar.return_value = None
        db.get.return_value = None
        with self.assertRaises(SolaceHTTPException) as ctx:
            scope_service.switch_scope(
                db,
                user,
                session,
                scope_type=SCOPE_ORGANIZATION,
                organization_id=uuid.uuid4(),
            )
        self.assertEqual(ctx.exception.status_code, 403)


class OperationalIsolationTests(unittest.TestCase):
    def test_list_users_filters_by_active_org(self) -> None:
        from app.core.scope_context import ActiveScope, set_active_scope
        from app.services.user_service import list_users

        org_a = uuid.uuid4()
        org_b = uuid.uuid4()
        db = MagicMock()
        user_a = CoreUser(
            id=uuid.uuid4(),
            username="a",
            organization_id=org_a,
            email="a@t.com",
            display_name="A",
        )
        user_b = CoreUser(
            id=uuid.uuid4(),
            username="b",
            organization_id=org_b,
            email="b@t.com",
            display_name="B",
        )

        class FakeScalars:
            def __init__(self, users):
                self._users = users

            def all(self):
                return self._users

        def scalars_side_effect(stmt):
            result = MagicMock()
            s = str(stmt)
            if "Core_UserRole" in s:
                result.all.return_value = []
            elif "CoreUser" in s or "Core_Users" in s:
                filtered = [u for u in [user_a, user_b] if u.organization_id == org_a]
                result.all.return_value = filtered
            else:
                result.all.return_value = []
            return result

        db.scalars.side_effect = scalars_side_effect
        token = set_active_scope(
            ActiveScope(SCOPE_ORGANIZATION, None, org_a, None, None)
        )
        try:
            from app.core.tenant_context import set_organization_id

            set_organization_id(org_a)
            rows = list_users(db, org_a)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["username"], "a")
        finally:
            from app.core.scope_context import reset_active_scope

            reset_active_scope(token)


class CompanyRegistryListTests(unittest.TestCase):
    def test_global_scope_user_lists_all_companies(self) -> None:
        from app.services.organization_service import _company_list_filters

        db = MagicMock()
        user_id = uuid.uuid4()
        db.scalar.return_value = uuid.uuid4()
        org_filter, country_filter = _company_list_filters(db, user_id)
        self.assertIsNone(org_filter)
        self.assertIsNone(country_filter)

    def test_org_scoped_user_lists_one_company(self) -> None:
        from app.core.scope_context import ActiveScope, reset_active_scope, set_active_scope
        from app.core.tenant_context import set_organization_id
        from app.services.organization_service import _company_list_filters

        org_id = uuid.uuid4()
        db = MagicMock()
        db.scalar.return_value = None
        token = set_active_scope(
            ActiveScope(SCOPE_ORGANIZATION, None, org_id, None, None)
        )
        set_organization_id(org_id)
        try:
            org_filter, country_filter = _company_list_filters(db, None)
            self.assertEqual(org_filter, org_id)
            self.assertIsNone(country_filter)
        finally:
            reset_active_scope(token)


class TenantBypassTests(unittest.TestCase):
    def test_system_bypass_token(self) -> None:
        token = enable_system_bypass("unit-test")
        try:
            from app.core.tenant_context import is_system_bypass

            self.assertTrue(is_system_bypass())
        finally:
            reset_system_bypass(token)


if __name__ == "__main__":
    unittest.main()
