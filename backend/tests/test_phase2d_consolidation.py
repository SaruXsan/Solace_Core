"""Phase 2D executive consolidation foundation tests."""

from __future__ import annotations

import unittest
import uuid
from unittest.mock import MagicMock

from app.core.ai_consolidation_policy import check_ai_consolidation_allowed
from app.core.consolidation_context import ActiveConsolidationScope, set_active_consolidation_scope
from app.core.exceptions import SolaceHTTPException
from app.core.scope_context import ActiveScope, set_active_scope
from app.models.platform import CoreConsolidationScope, CoreUser
from app.services import consolidation_scope_service as css
from app.services.consolidation_guard import ConsolidationAccessRequest, evaluate_consolidation_access


class ConsolidationSwitchTests(unittest.TestCase):
    def test_switch_rejects_unassigned_scope(self) -> None:
        db = MagicMock()
        user = CoreUser(id=uuid.uuid4(), organization_id=uuid.uuid4(), username="u")
        session = MagicMock()
        db.get.return_value = None
        db.scalar.return_value = None
        with self.assertRaises(SolaceHTTPException) as ctx:
            css.switch_consolidation_scope(
                db, user, session, uuid.uuid4(), ip_address="127.0.0.1"
            )
        self.assertEqual(ctx.exception.status_code, 403)

    def test_switch_activates_assigned_scope(self) -> None:
        db = MagicMock()
        user_id = uuid.uuid4()
        scope_id = uuid.uuid4()
        user = CoreUser(id=user_id, organization_id=uuid.uuid4(), username="u")
        session = MagicMock()
        scope = CoreConsolidationScope(
            id=scope_id,
            user_id=user_id,
            name="UAE Group",
            scope_level=css.LEVEL_COUNTRY,
            country_id=uuid.uuid4(),
            include_child_scopes=True,
            max_classification_allowed="Internal",
            can_view_raw_restricted=False,
            can_use_ai_summary=True,
            can_export=False,
            is_active=True,
        )
        db.scalar.return_value = scope
        db.get.return_value = scope
        active = css.switch_consolidation_scope(
            db, user, session, scope_id, ip_address="127.0.0.1"
        )
        self.assertIsNotNone(active)
        self.assertEqual(active.id, scope_id)


class ConsolidationGuardTests(unittest.TestCase):
    def _active(self, **kwargs) -> ActiveConsolidationScope:
        return ActiveConsolidationScope(
            id=kwargs.get("id", uuid.uuid4()),
            user_id=kwargs.get("user_id", uuid.uuid4()),
            scope_level=kwargs.get("scope_level", css.LEVEL_ORGANIZATION),
            country_id=kwargs.get("country_id"),
            organization_id=kwargs.get("organization_id"),
            branch_id=kwargs.get("branch_id"),
            department_id=kwargs.get("department_id"),
            include_child_scopes=True,
            max_classification_allowed=kwargs.get("max_classification_allowed", "Internal"),
            can_view_raw_restricted=kwargs.get("can_view_raw_restricted", False),
            can_use_ai_summary=kwargs.get("can_use_ai_summary", False),
            can_export=kwargs.get("can_export", False),
            allowed_modules=kwargs.get("allowed_modules"),
        )

    def test_classification_exceeds_ceiling(self) -> None:
        db = MagicMock()
        user_id = uuid.uuid4()
        user = CoreUser(id=user_id, organization_id=uuid.uuid4(), username="u")
        org_id = uuid.uuid4()
        active = self._active(user_id=user_id, organization_id=org_id, max_classification_allowed="Internal")
        scope_row = CoreConsolidationScope(
            id=active.id,
            user_id=user_id,
            name="Co",
            scope_level=css.LEVEL_ORGANIZATION,
            organization_id=org_id,
            include_child_scopes=True,
            max_classification_allowed="Internal",
            is_active=True,
        )
        db.get.return_value = scope_row

        def perm(db, u, code):
            return code == "consolidation.view"

        with unittest.mock.patch(
            "app.services.consolidation_guard.user_has_permission", side_effect=perm
        ):
            with unittest.mock.patch(
                "app.services.consolidation_guard.css.resolve_covered_entity_ids",
                return_value={
                    "countries": set(),
                    "organizations": {org_id},
                    "branches": set(),
                    "departments": set(),
                },
            ):
                result = evaluate_consolidation_access(
                    db,
                    user,
                    ConsolidationAccessRequest(
                        organization_ids=[org_id],
                        classification="Secret",
                    ),
                    active=active,
                    scope_row=scope_row,
                )
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "classification_exceeds_ceiling")

    def test_restricted_raw_denied_without_flag(self) -> None:
        db = MagicMock()
        user_id = uuid.uuid4()
        user = CoreUser(id=user_id, organization_id=uuid.uuid4(), username="u")
        org_id = uuid.uuid4()
        active = self._active(
            user_id=user_id,
            organization_id=org_id,
            can_view_raw_restricted=False,
        )
        scope_row = CoreConsolidationScope(
            id=active.id,
            user_id=user_id,
            name="Co",
            scope_level=css.LEVEL_ORGANIZATION,
            organization_id=org_id,
            include_child_scopes=True,
            max_classification_allowed="Restricted",
            can_view_raw_restricted=False,
            is_active=True,
        )
        db.get.return_value = scope_row

        def perm(db, u, code):
            return code in ("consolidation.view", "consolidation.view_restricted")

        with unittest.mock.patch(
            "app.services.consolidation_guard.user_has_permission", side_effect=perm
        ):
            with unittest.mock.patch(
                "app.services.consolidation_guard.css.resolve_covered_entity_ids",
                return_value={
                    "countries": set(),
                    "organizations": {org_id},
                    "branches": set(),
                    "departments": set(),
                },
            ):
                result = evaluate_consolidation_access(
                    db,
                    user,
                    ConsolidationAccessRequest(
                        organization_ids=[org_id],
                        classification="Internal",
                        requires_raw_restricted=True,
                    ),
                    active=active,
                    scope_row=scope_row,
                )
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "scope_raw_restricted_denied")


class OperationalIndependenceTests(unittest.TestCase):
    def test_operational_scope_independent_of_consolidation(self) -> None:
        org_a = uuid.uuid4()
        op_token = set_active_scope(
            ActiveScope("organization", None, org_a, None, None)
        )
        cons_token = set_active_consolidation_scope(
            ActiveConsolidationScope(
                id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                scope_level=css.LEVEL_GLOBAL,
                country_id=None,
                organization_id=None,
                branch_id=None,
                department_id=None,
                include_child_scopes=True,
                max_classification_allowed="Confidential",
                can_view_raw_restricted=False,
                can_use_ai_summary=True,
                can_export=True,
                allowed_modules=None,
            )
        )
        try:
            from app.core.scope_context import get_active_scope

            self.assertEqual(get_active_scope().organization_id, org_a)
        finally:
            from app.core.consolidation_context import reset_active_consolidation_scope
            from app.core.scope_context import reset_active_scope

            reset_active_consolidation_scope(cons_token)
            reset_active_scope(op_token)


class AIPolicyTests(unittest.TestCase):
    def test_ai_requires_consolidation_permission(self) -> None:
        db = MagicMock()
        user = CoreUser(id=uuid.uuid4(), organization_id=uuid.uuid4(), username="u")
        token = set_active_consolidation_scope(
            ActiveConsolidationScope(
                id=uuid.uuid4(),
                user_id=user.id,
                scope_level=css.LEVEL_GLOBAL,
                country_id=None,
                organization_id=None,
                branch_id=None,
                department_id=None,
                include_child_scopes=True,
                max_classification_allowed="Internal",
                can_view_raw_restricted=False,
                can_use_ai_summary=True,
                can_export=False,
                allowed_modules=None,
            )
        )
        try:

            def perm(db, u, code):
                return code == "consolidation.view"

            with unittest.mock.patch(
                "app.core.ai_consolidation_policy.user_has_permission", side_effect=perm
            ):
                with unittest.mock.patch(
                    "app.core.ai_consolidation_policy.evaluate_consolidation_access"
                ) as ev:
                    ev.return_value = unittest.mock.Mock(
                        allowed=True, reason="allowed", consolidation_scope_id="x"
                    )
                    result = check_ai_consolidation_allowed(db, user)
            self.assertFalse(result.allowed)
            self.assertEqual(result.reason, "missing_consolidation.ai_summary")
        finally:
            from app.core.consolidation_context import reset_active_consolidation_scope

            reset_active_consolidation_scope(token)


if __name__ == "__main__":
    unittest.main()
