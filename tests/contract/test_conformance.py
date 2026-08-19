# tests/contract/test_conformance.py
"""
Task F1 — Capability-contract conformance (provider-neutral; #18 adapter deferred).

Objective (spec §14, §21.2): prove a consumer depends on the CONTRACT, not Vault
APIs. This is a hermes-vault-owned contract concern.

The proofs here are static / source-level only:
  * The consumer-facing broker imports the provider-neutral contract (CapabilityRequest)
    and NEVER imports or calls hvac / Vault APIs directly.
  * The Capability envelope returned to a consumer contains NO secret material and NO
    provider-specific Vault fields (built on the A3 schema, which already forbids secret
    fields via `extra = "forbid"`).

No Vault runtime, no credentials, no live adapter (#18 deferred).
"""
import inspect
import json
import pathlib

from src.capability_contract.schema import CapabilityRequest, CapabilityType
from src.capability import broker as broker_mod  # noqa: F401  (RED until broker.py exists)
from src.capability_contract.broker import CapabilityBroker, Capability

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_CONTRACT_FILES = [
    _REPO_ROOT / "src" / "capability_contract" / "schema.py",
    _REPO_ROOT / "src" / "capability_contract" / "broker.py",
]


def _source(path: pathlib.Path) -> str:
    return path.read_text()


# ---------------------------------------------------------------------------
# Proof 1: consumer-facing contract modules never import/call Vault/hvac.
# ---------------------------------------------------------------------------
def test_contract_modules_never_import_vault():
    for f in _CONTRACT_FILES:
        assert f.exists(), f"expected contract module {f}"
        src = _source(f)
        assert "import hvac" not in src, f"{f} must not import hvac"
        assert "from hvac" not in src, f"{f} must not import hvac"
        assert "hvac." not in src, f"{f} must not reference hvac APIs"
        assert "vault.Client" not in src, f"{f} must not construct a Vault client"
        assert "hvac_client" not in src, f"{f} must not hold a Vault client"


# ---------------------------------------------------------------------------
# Proof 2: the broker depends on the CONTRACT request type, not a Vault client.
# ---------------------------------------------------------------------------
def test_broker_depends_on_contract_request():
    sig = inspect.signature(CapabilityBroker.request)
    assert sig.parameters["req"].annotation is CapabilityRequest, (
        "broker.request must accept the contract CapabilityRequest, not a Vault client"
    )
    src = _source(_REPO_ROOT / "src" / "capability_contract" / "broker.py")
    # Scan real code only (strip comments/docstrings) so the word in prose/docstrings
    # does not trip the check. A real `import hvac` / `from hvac` / `hvac.` is banned.
    code_lines = [
        ln for ln in src.splitlines()
        if not ln.lstrip().startswith("#")
    ]
    code = "\n".join(code_lines)
    assert ("from .schema import" in code) or (
        "from src.capability_contract.schema import" in code
    ), "broker must import the provider-neutral contract schema"
    assert "import hvac" not in code and "from hvac" not in code, "broker must not import hvac"
    assert "hvac." not in code, "broker must not call hvac APIs"


# ---------------------------------------------------------------------------
# Proof 3: the Capability envelope carries NO secret material.
# ---------------------------------------------------------------------------
def test_capability_envelope_has_no_secret_string():
    req = CapabilityRequest(
        principal="hsl-signer",
        action="transit.sign",
        resource_scope="hsl-transit/hsl-signing",
        risk_class="high",
        requested_ttl=120,
        capability_type=CapabilityType.wrapped_secret,
        request_id="req-f1-secret",
    )
    cap = CapabilityBroker().request(req)
    dumped = cap.model_dump()

    forbidden_field_names = {
        "token",
        "password",
        "secret",
        "vault_token",
        "client_token",
        "unwrap_token",
        "secret_id",
        "secretid",
        "recovery_key",
        "root_token",
        "private_key",
    }
    leaked = set(dumped.keys()) & forbidden_field_names
    assert not leaked, f"envelope must not carry secret fields: {leaked}"

    blob = json.dumps(dumped, default=str).lower()
    for pat in [
        "vault-",
        "s.",
        "root_token",
        "recovery_key",
        "secretid",
        "client_token",
        "unwrap_token",
        "password",
        "private_key",
        "-----begin",
    ]:
        assert pat not in blob, f"envelope leaked secret-like material: {pat}"

    assert cap.carries_secret() is False


# ---------------------------------------------------------------------------
# Proof 4: the Capability envelope is provider-neutral (no Vault-specific fields).
# ---------------------------------------------------------------------------
def test_capability_envelope_is_provider_neutral():
    req = CapabilityRequest(
        principal="hsl-signer",
        action="transit.sign",
        resource_scope="hsl-transit/hsl-signing",
        risk_class="medium",
        requested_ttl=300,
        request_id="req-f1-neutral",
    )
    cap = CapabilityBroker().request(req)
    dumped = cap.model_dump()

    for key in dumped.keys():
        assert not key.startswith("vault_"), f"provider-specific vault_ field: {key}"
        assert key not in {
            "auth_method",
            "mount_point",
            "namespace",
            "token_policies",
        }, f"Vault-specific field leaked: {key}"

    text = json.dumps(dumped, default=str)
    assert "VAULT-" not in text and "s." not in text


# ---------------------------------------------------------------------------
# Proof 5: a consumer path uses only the contract broker and receives a
#          no-secret envelope — it never obtains a Vault token to call directly.
# ---------------------------------------------------------------------------
def test_consumer_uses_broker_only():
    req = CapabilityRequest(
        principal="hermes-controller",
        action="transit.sign",
        resource_scope="hsl-transit/hsl-signing",
        risk_class="medium",
        requested_ttl=300,
        request_id="req-f1-consumer",
    )
    cap = CapabilityBroker().request(req)
    assert isinstance(cap, Capability)
    assert not cap.carries_secret()
    assert "token" not in cap.model_dump()
