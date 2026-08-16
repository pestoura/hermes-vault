from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

CAPABILITY_TYPES = {
    "delegated_operation",
    "dynamic_credential",
    "wrapped_secret",
    "memory_only",
    "tmpfs_file",
    "static_secret",
}
_REQUIRED_CORRELATION = (
    "execution_id",
    "plan_id",
    "request_id",
    "tool_call_id",
    "principal",
    "tool_identity",
    "action",
    "resource_scope",
    "risk_class",
)


def _required_string(data: dict[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _rfc3339(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class CapabilityRequest:
    execution_id: str
    plan_id: str
    request_id: str
    tool_call_id: str
    principal: str
    tool_identity: str
    action: str
    resource_scope: str
    risk_class: str
    requested_ttl_s: int
    capability_type: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CapabilityRequest":
        if not isinstance(data, dict):
            raise ValueError("capability request must be an object")
        fields = {name: _required_string(data, name) for name in _REQUIRED_CORRELATION}
        ttl = data.get("requested_ttl_s")
        if not isinstance(ttl, int) or isinstance(ttl, bool) or ttl <= 0 or ttl > 1800:
            raise ValueError("requested_ttl_s must be an integer between 1 and 1800")
        capability_type = _required_string(data, "capability_type")
        if capability_type not in CAPABILITY_TYPES:
            raise ValueError("unsupported capability_type")
        return cls(
            **fields,
            requested_ttl_s=ttl,
            capability_type=capability_type,
        )


@dataclass(frozen=True)
class CapabilityDescriptor:
    handle: str
    request_id: str
    execution_id: str
    tool_identity: str
    capability_type: str
    lease_id: str | None
    expires_at: str | None
    cleanup_required: bool
    status: str
    cleanup_status: str

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "handle": self.handle,
            "request_id": self.request_id,
            "execution_id": self.execution_id,
            "tool_identity": self.tool_identity,
            "capability_type": self.capability_type,
            "lease_id": self.lease_id,
            "expires_at": self.expires_at,
            "cleanup_required": self.cleanup_required,
            "status": self.status,
            "cleanup_status": self.cleanup_status,
        }


@dataclass
class PrivateCapability:
    handle: str
    request_id: str
    execution_id: str
    tool_identity: str
    capability_type: str
    material: bytearray
    lease_id: str | None
    expires_at: datetime | str | None
    cleanup_required: bool
    zeroized: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.material, bytearray):
            raise TypeError("private capability material must be bytearray")
        if not self.handle or not self.request_id or not self.execution_id or not self.tool_identity:
            raise ValueError("private capability identity fields must be non-empty")
        if self.capability_type not in CAPABILITY_TYPES:
            raise ValueError("unsupported private capability type")

    def zeroize(self) -> None:
        for index in range(len(self.material)):
            self.material[index] = 0
        self.zeroized = True

    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            handle=self.handle,
            request_id=self.request_id,
            execution_id=self.execution_id,
            tool_identity=self.tool_identity,
            capability_type=self.capability_type,
            lease_id=self.lease_id,
            expires_at=_rfc3339(self.expires_at),
            cleanup_required=self.cleanup_required,
            status="ACTIVE",
            cleanup_status="PENDING" if self.cleanup_required else "NOT_REQUIRED",
        )
