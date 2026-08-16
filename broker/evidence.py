from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from broker.model import CapabilityDescriptor, CapabilityRequest
from broker.redaction import sanitize

EVIDENCE_SCHEMA = "hermes-vault-broker-evidence/v1"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_broker_evidence(
    request: CapabilityRequest,
    descriptor: CapabilityDescriptor,
    *,
    final_status: str,
    error_category: str | None = None,
) -> dict[str, Any]:
    evidence = {
        "schema": EVIDENCE_SCHEMA,
        "observed_at": _now(),
        "execution_id": request.execution_id,
        "plan_id": request.plan_id,
        "request_id": request.request_id,
        "tool_call_id": request.tool_call_id,
        "principal": request.principal,
        "tool_identity": request.tool_identity,
        "action": request.action,
        "resource_scope": request.resource_scope,
        "risk_class": request.risk_class,
        "capability_type": descriptor.capability_type,
        "capability_handle": descriptor.handle,
        "lease_id": descriptor.lease_id,
        "expires_at": descriptor.expires_at,
        "cleanup_required": descriptor.cleanup_required,
        "final_status": final_status,
        "capability_status": descriptor.status,
        "cleanup_status": descriptor.cleanup_status,
        "error_category": error_category,
    }
    return sanitize(evidence)
