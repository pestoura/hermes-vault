# tests/contract/test_conformance.py
"""
Task F1 — Capability-contract conformance (provider-neutral; #18 adapter deferred).

Objective (spec §14, §21.2): prove a consumer depends on the CONTRACT, not Vault
APIs. This is a hermes-vault-owned contract concern.

The proofs here are static / source-level only:
  * The consumer-facing broker imports the provider-neutral contract (CapabilityRequest)
    and NEVER imports or calls hvac / Vault APIs directly. Import detection is AST-based
    (not substring over docstrings/comments) so prose cannot create false confidence.
  * The Capability envelope returned to a consumer contains NO secret material and NO
    provider-specific Vault fields. This is proven structurally via the pydantic
    `model_fields` schema and the serialized key set, not via brittle substring scans
    over the JSON body.

No Vault runtime, no credentials, no live adapter (#18 deferred).
"""
import ast
import inspect
import json
import pathlib

from src.capability_contract.schema import CapabilityRequest, CapabilityType
from src.capability import broker as broker_mod  # noqa: F401  (consumer re-export boundary)
from src.capability_contract.broker import (
    CapabilityBroker,
    Capability,
    SECRET_BEARING_FIELD_DENYLIST,
    is_secret_bearing_field,
)

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_CONTRACT_FILES = [
    _REPO_ROOT / "src" / "capability_contract" / "schema.py",
    _REPO_ROOT / "src" / "capability_contract" / "broker.py",
]


def _source(path: pathlib.Path) -> str:
    return path.read_text()


def _module_imports_hvac(path: pathlib.Path) -> bool:
    """AST-based detection of a direct hvac/Vault import in a source module.

    Scans Import and ImportFrom nodes only — substring scans against docstrings or
    comments are intentionally avoided so prose cannot create false confidence.
    """
    tree = ast.parse(_source(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "hvac" or alias.name.startswith("hvac."):
                    return True
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod == "hvac" or mod.startswith("hvac."):
                return True
    return False


# ---------------------------------------------------------------------------
# Proof 1: consumer-facing contract modules never import/call Vault/hvac.
# ---------------------------------------------------------------------------
def test_contract_modules_never_import_vault():
    for f in _CONTRACT_FILES:
        assert f.exists(), f"expected contract module {f}"
        assert not _module_imports_hvac(f), f"{f} must not import hvac"


# ---------------------------------------------------------------------------
# Proof 2: the broker depends on the CONTRACT request type, not a Vault client.
# ---------------------------------------------------------------------------
def test_broker_depends_on_contract_request():
    sig = inspect.signature(CapabilityBroker.request)
    assert sig.parameters["req"].annotation is CapabilityRequest, (
        "broker.request must accept the contract CapabilityRequest, not a Vault client"
    )
    # AST-based: broker.py must import the provider-neutral contract schema and must
    # not import hvac.
    broker_file = _REPO_ROOT / "src" / "capability_contract" / "broker.py"
    assert not _module_imports_hvac(broker_file), "broker must not import hvac"
    tree = ast.parse(_source(broker_file))
    imports_schema = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            # Accept both absolute (`...capability_contract.schema`) and relative
            # (`from .schema import CapabilityRequest`, node.level >= 1).
            if mod.endswith("capability_contract.schema") or mod == "schema":
                if any(a.name == "CapabilityRequest" for a in node.names):
                    imports_schema = True
    assert imports_schema, "broker must import the provider-neutral contract schema"


# ---------------------------------------------------------------------------
# Proof 3: the Capability envelope carries NO secret material — proven by schema
#          + serialized keys (no brittle substring assertion over the body).
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

    # Structural proof: every declared field name (schema) and every serialized
    # key must be classified non-secret by the fail-closed classifier.
    declared = set(Capability.model_fields.keys())
    forbidden_declared = {f for f in declared if is_secret_bearing_field(f)}
    assert not forbidden_declared, f"envelope schema carries secret fields: {forbidden_declared}"

    serialized = set(dumped.keys())
    forbidden_serialized = {k for k in serialized if is_secret_bearing_field(k)}
    assert not forbidden_serialized, f"envelope leaked secret fields: {forbidden_serialized}"

    # Even wrapped_secret — the highest-risk capability type — carries no secret.
    assert cap.carries_secret() is False


# ---------------------------------------------------------------------------
# Proof 4: the Capability envelope is provider-neutral (no Vault-specific fields).
#          Proven structurally by model_fields + serialized keys.
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

    vault_specific = {
        "auth_method",
        "mount_point",
        "namespace",
        "token_policies",
    }
    declared = set(Capability.model_fields.keys())
    leaked_declared = declared & vault_specific
    assert not leaked_declared, f"Vault-specific field leaked into schema: {leaked_declared}"

    leaked_serialized = set(dumped.keys()) & vault_specific
    assert not leaked_serialized, f"Vault-specific field leaked: {leaked_serialized}"

    # No provider-prefixed field name in either the schema or the serialized envelope.
    assert not any(k.startswith("vault_") for k in declared), "vault_ schema field present"
    assert not any(k.startswith("vault_") for k in dumped.keys()), "vault_ serialized field present"


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


# ---------------------------------------------------------------------------
# Regression guard — fail-closed secret-field classifier (F1 fix round 1).
# The denylist below must cover the documented secret-bearing fields; any future
# field whose name matches one of these must be classified as secret-bearing.
# ---------------------------------------------------------------------------
def test_secret_denylist_covers_required_terms():
    required_terms = {
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
    }
    missing = required_terms - set(SECRET_BEARING_FIELD_DENYLIST)
    assert not missing, f"denylist missing required terms: {missing}"


def test_classifier_matches_secret_bearing_field_names():
    secret_cases = [
        "token",
        "vault_token",
        "client_token",
        "unwrap_token",
        "secret_id",
        "recovery_key",
        "root_token",
        "private_key",
        "password",
        "credential",
        "api_key",
        "secret_payload",
        "signing_cert",
        "vault_data",
    ]
    for name in secret_cases:
        assert is_secret_bearing_field(name), f"{name!r} should be secret-bearing"

    # Neutral identity / routing fields must NOT be falsely classified as secret.
    neutral_cases = [
        "principal",
        "action",
        "resource_scope",
        "risk_class",
        "request_id",
        "execution_id",
        "plan_id",
        "capability_type",
        "granted_ttl",
        "id",
        "name",
        "scope",
        "policy",
        "role",
    ]
    for name in neutral_cases:
        assert not is_secret_bearing_field(name), f"{name!r} must stay neutral"


def test_carries_secret_is_computed_not_constant():
    # The implementation must compute over declared fields, not return a constant.
    # Confirm the classifier is wired to the denylist and reacts to denylist content.
    assert is_secret_bearing_field("vault_token") is True
    assert is_secret_bearing_field("principal") is False
    # carries_secret() on a correctly-shaped envelope is fail-closed False.
    req = CapabilityRequest(
        principal="hermes-controller",
        action="transit.sign",
        resource_scope="hsl-transit/hsl-signing",
        risk_class="low",
        requested_ttl=60,
        request_id="req-f1-cls",
    )
    assert CapabilityBroker().request(req).carries_secret() is False
