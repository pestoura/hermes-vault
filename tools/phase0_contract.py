from __future__ import annotations

from pathlib import Path
from typing import Sequence

from tools.phase0_collectors import (
    _utc_now,
    collect_docker,
    collect_host,
    collect_listeners,
    collect_storage,
    collect_systemd,
)
from tools.phase0_prerequisites import (
    collect_recovery_constraints,
    collect_tls_metadata,
    collect_vault_prerequisites,
)
from tools.phase0_references import collect_secret_references

REPORT_SCHEMA = "hermes-vault-phase0-discovery/v1"
_MANDATORY_DISCOVERY_SECTIONS = (
    "host",
    "storage",
    "systemd",
    "docker",
    "listeners",
    "tls",
    "vault_prerequisites",
)
_DEFAULT_REFERENCE_PATHS = (
    Path("/home/estourpm/.hermes/.env"),
    Path("/home/estourpm/.config/systemd/user/hermes-gateway.service"),
    Path("/home/estourpm/.config/systemd/user/hermes-dashboard.service"),
    Path("/home/estourpm/.config/systemd/user/cloudflared-hermes-mcp.service"),
)


def _section_is_conclusive(name: str, section: object) -> bool:
    if not isinstance(section, dict):
        return False
    if name == "vault_prerequisites":
        observed = section.get("observed")
        target = section.get("target")
        return (
            section.get("mutation_performed") is False
            and isinstance(observed, dict)
            and isinstance(observed.get("docker"), dict)
            and observed["docker"].get("status") == "present"
            and isinstance(target, dict)
            and target.get("version") == "1.21.4"
            and target.get("edition") == "community"
            and target.get("tls_required") is True
        )
    return section.get("status") == "ok" and section.get("available") is True


def evaluate_phase0(sections: dict) -> dict:
    missing = [name for name in _MANDATORY_DISCOVERY_SECTIONS if not _section_is_conclusive(name, sections.get(name))]
    return {
        "DISCOVERY_COMPLETE": {
            "status": "PASS" if not missing else "FAIL",
            "missing_or_inconclusive": missing,
            "authority": "deterministic_discovery_contract",
        },
        "NO_SECRET_IN_REPO": {"status": "NOT_EVALUATED", "authority": "separate_repository_secret_scan"},
        "TARGET_ARCHITECTURE_APPROVED": {"status": "NOT_EVALUATED", "authority": "human_governance_decision"},
        "RECOVERY_DESIGN_DEFINED": {"status": "NOT_EVALUATED", "authority": "separate_recovery_design_review"},
    }


def build_report(*, sections: dict, secret_references: list[dict], recovery_design: dict) -> dict:
    return {
        "schema": REPORT_SCHEMA,
        "generated_at": _utc_now(),
        "mode": "read_only",
        "mutation_performed": False,
        "sections": sections,
        "secret_references": secret_references,
        "recovery_design": recovery_design,
        "gates": evaluate_phase0(sections),
    }


def collect_phase0_report(*, reference_paths: Sequence[Path] = _DEFAULT_REFERENCE_PATHS, cert_paths: Sequence[Path] = (), vault_binary: str | None = None) -> dict:
    sections = {
        "host": collect_host(),
        "storage": collect_storage(),
        "systemd": collect_systemd(),
        "docker": collect_docker(),
        "listeners": collect_listeners(),
        "tls": collect_tls_metadata(cert_paths),
        "vault_prerequisites": collect_vault_prerequisites(vault_binary=vault_binary),
    }
    return build_report(
        sections=sections,
        secret_references=collect_secret_references(reference_paths),
        recovery_design=collect_recovery_constraints(),
    )
