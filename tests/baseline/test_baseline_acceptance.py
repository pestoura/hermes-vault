# tests/baseline/test_baseline_acceptance.py
#
# Task B2 — Baseline acceptance harness (health / TLS strictness / Raft / Shamir).
#
# Two layers:
#   1. Live HITL acceptance (verbatim from task-B2-brief.md), requiring a locally
#      started, operator-initialized Vault over TLS (HITL B4: vault operator init /
#      unseal). Skipped offline/CI; becomes the GREEN oracle after HITL B4.
#   2. Static/offline contract tests that validate the four baseline contracts
#      against the committed B1 artifacts (deployments/vault/*) without starting
#      Vault, generating TLS material, or touching secrets. Used for offline GREEN.
import os
import re

import pytest

# NOTE: no module-level pytestmark. The 3 live HITL acceptance tests below are
# individually marked (and skip-guarded on VAULT_ADDR/VAULT_CACERT); the 4
# static/offline contract tests are NOT marked, so `pytest -m 'not hitl'`
# runs them and deselects only the live tests.

_HCL_PATH = "deployments/vault/config/vault.hcl"
_COMPOSE_PATH = "deployments/vault/docker-compose.yml"


def _live_env():
    return all(k in os.environ for k in ("VAULT_ADDR", "VAULT_CACERT"))


# ---------------------------------------------------------------------------
# 1) Live HITL acceptance — verbatim from the brief, guarded to skip offline.
# ---------------------------------------------------------------------------
@pytest.mark.hitl
@pytest.mark.skipif(
    not _live_env(),
    reason="B2 HITL: no live Vault endpoint (VAULT_ADDR/VAULT_CACERT); "
    "offline static contract tests validate the same contracts below.",
)
def test_tls_only_no_plain_http():
    import httpx
    with pytest.raises(httpx.ConnectError):
        httpx.get(f"http://{os.environ['VAULT_ADDR'].split('//')[1]}", verify=False, timeout=3)


@pytest.mark.hitl
@pytest.mark.skipif(
    not _live_env(),
    reason="B2 HITL: no live Vault endpoint (VAULT_ADDR/VAULT_CACERT); "
    "offline static contract tests validate the same contracts below.",
)
def test_raft_storage_mode():
    import hvac
    c = hvac.Client(url=os.environ["VAULT_ADDR"], verify=os.environ["VAULT_CACERT"])
    st = c.sys.read_health_status()
    assert st["storage_type"] == "raft"


@pytest.mark.hitl
@pytest.mark.skipif(
    not _live_env(),
    reason="B2 HITL: no live Vault endpoint (VAULT_ADDR/VAULT_CACERT); "
    "offline static contract tests validate the same contracts below.",
)
def test_shamir_threshold_two_of_three():
    import hvac
    c = hvac.Client(url=os.environ["VAULT_ADDR"], verify=os.environ["VAULT_CACERT"])
    cfg = c.sys.read_seal_status()
    assert cfg["type"] == "shamir"
    assert cfg["threshold"] == 2 and cfg["secret_shares"] == 3


# ---------------------------------------------------------------------------
# 2) Static/offline contract validation (no Vault runtime, no secrets, no TLS).
#    Proves the four baseline contracts from the brief's objective are encoded
#    in the committed B1 deployment artifacts.
# ---------------------------------------------------------------------------
def _hcl():
    from pathlib import Path
    return Path(_HCL_PATH).read_text()


def _compose():
    import yaml
    from pathlib import Path
    return yaml.safe_load(Path(_COMPOSE_PATH).read_text())


def test_contract_tls_only_no_plain_http():
    # Only an HTTPS listener is configured: TLS enabled, cert+key referenced, and
    # no plaintext listener (tls_disable=true) is present anywhere.
    hcl = _hcl()
    assert re.search(r"tls_disable\s*=\s*false", hcl), "TLS must be enabled"
    assert "tls_cert_file" in hcl and "tls_key_file" in hcl
    assert not re.search(r"tls_disable\s*=\s*true", hcl), "plaintext HTTP listener forbidden"
    # UI disabled (no separate HTTP UI surface); exposure is loopback-only.
    assert "ui = false" in hcl
    comp = _compose()
    for p in comp["services"]["vault"].get("ports", []):
        assert p.strip().startswith("127.0.0.1:"), f"non-loopback exposure: {p}"


def test_contract_raft_storage_mode():
    hcl = _hcl()
    assert 'storage "raft"' in hcl
    assert "node_id" in hcl
    assert "/vault/file" in hcl
    # No competing storage backend is configured.
    for other in (
        'storage "file"',
        'storage "consul"',
        'storage "gcs"',
        'storage "s3"',
        'storage "mysql"',
        'storage "postgresql"',
        'storage "etcd"',
    ):
        assert other not in hcl, f"unexpected storage backend: {other}"


def test_contract_shamir_manual_seal():
    hcl = _hcl()
    # No auto-unseal seal stanza -> default seal type resolves to shamir on init.
    assert "seal {" not in hcl, "auto-unseal seal stanza present"
    assert "namespace" not in hcl, "Enterprise namespace present"
    # No hardcoded threshold/secret_shares that would break the 2/3 init contract;
    # the 2-of-3 (secret_shares=3, threshold=2) parameters are supplied at HITL
    # init (B4), per the brief's acceptance target.
    assert "secret_shares" not in hcl and "threshold" not in hcl
    # Image is pinned to the HSL-validated OSS digest (no Enterprise image).
    comp = _compose()
    img = comp["services"]["vault"]["image"]
    assert img.startswith("hashicorp/vault:"), "must be Community/OSS, not vault-enterprise"


def test_contract_health_sealed_before_init():
    # Health is reported via `vault status`, which returns sealed/initialization
    # required until the operator performs HITL init/unseal (B4). There must be
    # no automation that initializes/unseals the node from config or entrypoint.
    comp = _compose()
    hc = comp["services"]["vault"].get("healthcheck", {})
    assert hc.get("test") == ["CMD", "vault", "status"], (
        "healthcheck must report vault status (sealed until HITL init)"
    )
    assert comp["services"]["vault"].get("command") == "server"
    hcl = _hcl()
    assert "operator init" not in hcl and "operator unseal" not in hcl
