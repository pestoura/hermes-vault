from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_serializer

class CapabilityType(str, Enum):
    delegated_operation = "delegated_operation"
    ephemeral_token = "ephemeral_token"
    wrapped_secret = "wrapped_secret"
    certificate = "certificate"
    dynamic_credential = "dynamic_credential"

class CapabilityRequest(BaseModel):
    # NO secret-material fields by design (spec §14). Delivery is handled separately.
    principal: str
    action: str
    resource_scope: str
    risk_class: str
    requested_ttl: int = Field(ge=0, le=3600)
    capability_type: Optional[CapabilityType] = None
    execution_id: Optional[str] = None
    plan_id: Optional[str] = None
    request_id: Optional[str] = None

    model_config = {"extra": "forbid"}  # reject unexpected fields incl. any secret payload

    @field_serializer("capability_type")
    def _serialize_capability_type(self, value: Optional[CapabilityType]) -> Optional[str]:
        # Emit a provider-neutral wire value string, not the Python Enum object.
        # The live model attribute remains strongly typed as CapabilityType.
        return value.value if value is not None else None
