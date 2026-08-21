from pathlib import Path

import yaml


ADR = Path("docs/13-security-decisions.md")
SPEC = Path("docs/specs/2026-08-18-hermes-shared-vault-service-design.md")
COMPOSE = Path("deployments/vault/docker-compose.yml")
TLS_SCRIPT = Path("deployments/vault/scripts/provision-tls.sh")
CONTINUITY = Path("docs/runbooks/hsl-key-continuity.md")
DECOMMISSION = Path("docs/runbooks/hsl-decommission.md")
MIGRATION = Path("docs/plans/hsl-consumer-migration-boundary.md")


def _text(path: Path) -> str:
    return path.read_text()


def test_adr_018_preserves_historical_verification_without_resigning():
    text = _text(ADR)
    assert "ADR-018" in text
    assert "verify-only" in text
    assert "hermes-lab-l1-signer" in text
    assert "re-sign" in text.lower() or "reassinar" in text.lower()


def test_adr_019_private_security_plane_contract():
    text = _text(ADR)
    assert "ADR-019" in text
    assert "ADR-019A" in text
    assert "hermes-security-plane" in text
    assert "hermes-vault-admin" in text
    assert "internal: true" in text
    assert "127.0.0.1:8200" in text
    assert "hermes-vault" in text


def test_adr_020_controlled_parallel_run_contract():
    text = _text(ADR)
    assert "ADR-020" in text
    assert "parallel-run" in text.lower()
    assert "verify-only" in text
    assert "new evidence" in text.lower() or "nova evidência" in text.lower()


def test_adr_021_shamir_custody_is_out_of_band_and_not_located_in_repo():
    text = _text(ADR)
    assert "ADR-021" in text
    assert "Shamir 3/2" in text
    assert "out-of-band" in text
    assert "three independent" in text.lower() or "três" in text.lower()
    assert "concrete" in text.lower() or "concreta" in text.lower()
    assert "GitHub" in text and "Hermes" in text and "Jarvas" in text


def test_spec_section_25_records_all_resolutions_without_runtime_claim():
    text = _text(SPEC)
    assert text.count("RESOLVED 2026-08-21") >= 5
    assert "verify-only" in text
    assert "hermes-security-plane" in text
    assert "parallel-run" in text.lower()
    assert "Shamir 3/2" in text
    assert "hashicorp/vault:1.21.4" in text
    assert "does not claim live implementation" in text.lower()


def test_resolved_spec_has_no_stale_open_decision_language():
    text = _text(SPEC)
    low = text.lower()
    assert "exact bind/port is an owner decision" not in low
    assert "key-continuity decision (§19) is made" not in text
    assert "ADR-019" in text and "hermes-security-plane" in text
    assert "ADR-018" in text and "ADR-020" in text


def test_spec_status_matches_verified_unsealed_health_runtime_without_promoting_readiness():
    text = _text(SPEC)
    assert "Design / specification only. Not implemented." not in text
    assert "repository-side implementation" in text.lower()
    assert "Live Vault deployment/start: `VERIFIED_PRE_INIT`" in text
    assert "Vault initialization: `VERIFIED_INITIALIZED_SEALED`" in text
    assert "Vault unseal: `VERIFIED_UNSEALED_HEALTHY`" in text
    assert "VAULT_HEALTH_PASS" in text and "VAULT_UNSEALED" in text
    assert "HTTP 200" in text
    assert "sealed=false" in text
    assert "UNSEALED_READY" in text
    assert "audit" in text.lower() and "NOT_RUN" in text
    assert "original design/spec change" in text.lower()
    assert "current implementation acceptance" in text.lower()


def test_compose_uses_private_internal_security_plane_and_loopback_publication():
    comp = yaml.safe_load(_text(COMPOSE))
    vault = comp["services"]["vault"]
    assert vault.get("ports") == ["127.0.0.1:8200:8200"]
    nets = vault.get("networks", {})
    assert "hermes-security-plane" in nets
    assert "hermes-vault-admin" in nets
    net_cfg = nets["hermes-security-plane"] or {}
    assert "hermes-vault" in net_cfg.get("aliases", [])
    top = comp.get("networks", {}).get("hermes-security-plane", {})
    assert top.get("name") == "hermes-security-plane"
    assert top.get("internal") is True
    admin = comp.get("networks", {}).get("hermes-vault-admin", {})
    assert admin.get("name") == "hermes-vault-admin"
    assert admin.get("internal") is False
    assert admin.get("driver_opts", {}).get("com.docker.network.bridge.enable_ip_masquerade") == "false"


def test_operator_tls_contract_includes_internal_and_loopback_sans():
    src = _text(TLS_SCRIPT)
    assert "VAULT_TLS_OPERATOR_ACK" in src
    for san in ("DNS:hermes-vault", "DNS:localhost", "IP:127.0.0.1"):
        assert san in src
    assert "subjectAltName" in src
    assert "vault operator init" not in src
    assert "operator unseal" not in src
    assert "vault server" not in src


def test_transition_runbooks_define_controlled_states_and_acceptance_gates():
    assert CONTINUITY.is_file()
    combined = "\n".join((_text(CONTINUITY), _text(DECOMMISSION), _text(MIGRATION)))
    for state in (
        "LEGACY_SIGN_ACTIVE",
        "PARALLEL_SHARED_PENDING_ACCEPTANCE",
        "SHARED_SIGN_ACTIVE_LEGACY_VERIFY_ONLY",
        "LEGACY_VERIFY_RETIRED",
    ):
        assert state in combined
    for gate in (
        "AUDIT_PASS",
        "RESTORE_DRILL_PASS",
        "TLS_CONNECTIVITY_PASS",
        "HSL_ISOLATION_PASS",
        "SIGN_VERIFY_PASS",
    ):
        assert gate in combined
    assert "bulk re-sign" in combined.lower() or "bulk re-signing" in combined.lower()
    assert "pestoura/hermes-security-labs" in combined
    assert "NOT executed" in combined or "NOT_RUN" in combined
