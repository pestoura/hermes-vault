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

def test_rejects_secret_material():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        CapabilityRequest(principal="x", action="y",
                          resource_scope="z", risk_class="low",
                          requested_ttl=60,
                          _secret_value="VAULT-TOKEN-XXXX")  # field must not exist
