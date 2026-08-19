"""Provider-neutral capability broker + consumer envelope (spec §14, A3).

This module is the contract boundary: a consumer depends on `CapabilityRequest`
and receives a no-secret `Capability` envelope. It MUST NOT import or call any
Vault/hvac API — the concrete provider (#18) is deferred and delivers the live
credential out-of-band, never embedded in this envelope.
"""
from typing import Optional

from pydantic import BaseModel

from .schema import CapabilityRequest


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
        return False


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
