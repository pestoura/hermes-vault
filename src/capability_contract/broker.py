"""Provider-neutral capability broker + consumer envelope (spec §14, A3).

This module is the contract boundary: a consumer depends on `CapabilityRequest`
and receives a no-secret `Capability` envelope. It MUST NOT import or call any
Vault/hvac API — the concrete provider (#18) is deferred and delivers the live
credential out-of-band, never embedded in this envelope.
"""
from typing import Optional

from pydantic import BaseModel

from .schema import CapabilityRequest

# Documented denylist of field-name fragments that signal a secret-bearing payload.
# Matching is fail-closed: any declared/envelope field whose name contains one of
# these fragments is treated as carrying secret material. Neutral identity/routing
# fields (principal, action, resource_scope, risk_class, request_id, execution_id,
# plan_id, capability_type, granted_ttl) are intentionally NOT in this list so they
# are not falsely classified as secrets.
SECRET_BEARING_FIELD_DENYLIST = (
    "token",
    "password",
    "secret",
    "credential",
    "key",
    "payload",
    "cert",
    "data",
    "vault_token",
    "client_token",
    "unwrap_token",
    "secret_id",
    "recovery_key",
    "root_token",
    "private_key",
)


def is_secret_bearing_field(name: str) -> bool:
    """Fail-closed check: does a field name signal secret material?

    Substring match against the documented denylist. Case-insensitive. A name is
    classified secret-bearing if it CONTAINS any denylist fragment, so both exact
    names (`token`) and compositions (`vault_token`, `api_key`, `secret_payload`)
    are caught. Neutrally-named fields contain none of the fragments and stay False.
    """
    lowered = name.lower()
    return any(frag in lowered for frag in SECRET_BEARING_FIELD_DENYLIST)


class Capability(BaseModel):
    """Provider-neutral envelope returned to a consumer.

    Deliberately carries NO secret material and NO Vault-specific fields. The live
    credential/operation is delivered separately by the (deferred, #18) provider.
    """

    principal: str
    capability_type: Optional[str] = None
    action: str
    resource_scope: str
    risk_class: str
    granted_ttl: int
    request_id: Optional[str] = None
    execution_id: Optional[str] = None
    plan_id: Optional[str] = None

    model_config = {"extra": "forbid"}

    def carries_secret(self) -> bool:
        """Computed, fail-closed check over the declared envelope schema.

        Returns True if ANY declared model field name is classified as
        secret-bearing by `is_secret_bearing_field`. For the current contract the
        declared fields are all neutral, so this evaluates to False — but the result
        is derived from the schema, not a hardcoded constant, so an accidental
        secret-bearing field addition would be caught.
        """
        return any(is_secret_bearing_field(f) for f in type(self).model_fields)


class CapabilityBroker:
    """Provider-neutral broker.

    A consumer calls `request(req)` with a contract `CapabilityRequest` and receives
    a `Capability` envelope. No Vault client, no token, no secret material.
    """

    def request(self, req: CapabilityRequest) -> Capability:
        return Capability(
            principal=req.principal,
            capability_type=req.capability_type.value if req.capability_type else None,
            action=req.action,
            resource_scope=req.resource_scope,
            risk_class=req.risk_class,
            granted_ttl=req.requested_ttl,
            request_id=req.request_id,
            execution_id=req.execution_id,
            plan_id=req.plan_id,
        )
