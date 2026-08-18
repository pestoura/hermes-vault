# tests/contract/test_capability_contract.py
from src.capability_contract.schema import CapabilityRequest, CapabilityType

def test_required_fields_present():
    r = CapabilityRequest(
        principal="hermes-controller",
        action="transit.sign",
        resource_scope="hsl-transit/hsl-signing",
        risk_class="medium",
        requested_ttl=300,
    )
    assert r.capability_type is None or isinstance(r.capability_type, CapabilityType)

def test_capability_type_serializes_to_wire_string():
    # Reviewer Important finding: model_dump() must emit a provider-neutral
    # wire value string for capability_type, not a Python Enum object.
    # The live model attribute stays strongly typed as CapabilityType.
    r = CapabilityRequest(
        principal="hermes-controller",
        action="transit.sign",
        resource_scope="hsl-transit/hsl-signing",
        risk_class="medium",
        requested_ttl=300,
        capability_type=CapabilityType.ephemeral_token,
    )
    dumped = r.model_dump()
    ct = dumped["capability_type"]
    assert type(ct) is str  # wire value is a plain string, not an Enum object
    assert ct == CapabilityType.ephemeral_token.value
    assert isinstance(r.capability_type, CapabilityType)  # attribute stays typed


def test_rejects_secret_material():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        CapabilityRequest(principal="x", action="y",
                          resource_scope="z", risk_class="low",
                          requested_ttl=60,
                          _secret_value="VAULT-TOKEN-XXXX")  # field must not exist
