"""WP-SEC-003 slice 1: deny-by-default Core authorization policy.

A pure decision over a closed catalog of protected manufacturing actions. It
reads no identity, session, token, configuration or secret, calls no service
and changes nothing; the caller supplies the permissions it already holds.

The action identifiers are the candidate Action Catalog members of
02_System_Architecture_Specification. The exact RBAC permission matrix is still
an open question (01 Item 5), so every permission string below is a
provisional, action-scoped name, and each ``core_entrypoint`` is a reserved
reference to a Core command handler that does not exist yet. Neither is bound
to code or certified by this module, and this module is not an HTTP, IdP or
Automation enforcement point.
"""

from collections.abc import Collection, Mapping
from enum import StrEnum
from types import MappingProxyType
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

_Token = Annotated[str, StringConstraints(strict=True, pattern=r"^\S+$")]


class Decision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class ProtectedAction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action_id: _Token
    required_permission: _Token
    core_entrypoint: _Token


def _build_catalog(*actions: ProtectedAction) -> Mapping[str, ProtectedAction]:
    for field in ("action_id", "required_permission", "core_entrypoint"):
        values = [getattr(action, field) for action in actions]
        if len(set(values)) != len(values):
            raise ValueError(f"duplicate protected-action {field}")
    return MappingProxyType({action.action_id: action for action in actions})


def _action(action_id: str, permission: str, entrypoint: str) -> ProtectedAction:
    return ProtectedAction(
        action_id=action_id,
        required_permission=permission,
        core_entrypoint=f"manufacturing_core.commands.{entrypoint}",
    )


PROTECTED_ACTIONS: Mapping[str, ProtectedAction] = _build_catalog(
    _action("PlaceLotOnHold", "core.lot.place_hold", "place_lot_on_hold"),
    _action(
        "ReleaseMaterialHold", "core.material.release_hold", "release_material_hold"
    ),
    _action("IsolateMachine", "core.machine.isolate", "isolate_machine"),
    _action(
        "ReleaseMachineIsolation",
        "core.machine.release_isolation",
        "release_machine_isolation",
    ),
    _action("ActivateSchedule", "core.schedule.activate", "activate_schedule"),
    _action(
        "CreateMaintenanceWorkOrder",
        "core.maintenance.create_work_order",
        "create_maintenance_work_order",
    ),
    _action("UpdateLotPriority", "core.lot.update_priority", "update_lot_priority"),
    _action(
        "ExecuteApprovedReworkDirective",
        "core.rework.execute_approved",
        "execute_approved_rework_directive",
    ),
)


def evaluate(principal_permissions: Collection[str] | None, action: str) -> Decision:
    """Return ALLOW only for a catalogued action whose exact permission is held.

    Anything else is DENY: an unknown or non-string action, missing or malformed
    permissions, a single string given instead of a collection, and any
    permission that is not an exact, case-sensitive match. There are no
    wildcards, roles, inheritance or normalization.
    """
    if not isinstance(action, str):
        return Decision.DENY
    entry = PROTECTED_ACTIONS.get(action)
    if entry is None:
        return Decision.DENY
    if not isinstance(principal_permissions, Collection) or isinstance(
        principal_permissions, str | bytes | bytearray
    ):
        return Decision.DENY
    if any(
        isinstance(permission, str) and permission == entry.required_permission
        for permission in principal_permissions
    ):
        return Decision.ALLOW
    return Decision.DENY
