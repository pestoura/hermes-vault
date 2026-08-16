from __future__ import annotations

import re
from pathlib import Path
from typing import Sequence

from tools.phase0_collectors import _utc_now
from tools.phase0_core import run_command

_PRIVATE_KEY_PATH_HINT = re.compile(r"(?i)(?:private|server|client|tls|ca)?[-_.]?(?:key|privkey)(?:[-_.]|$)")


def _parse_openssl_metadata(text: str) -> dict[str, str | None]:
    result: dict[str, str | None] = {
        "subject": None,
        "issuer": None,
        "serial": None,
        "not_before": None,
        "not_after": None,
        "sha256_fingerprint": None,
    }
    for line in text.splitlines():
        stripped = line.strip()
        lower = stripped.lower()
        if lower.startswith("subject="):
            result["subject"] = stripped.split("=", 1)[1].strip()
        elif lower.startswith("issuer="):
            result["issuer"] = stripped.split("=", 1)[1].strip()
        elif lower.startswith("serial="):
            result["serial"] = stripped.split("=", 1)[1].strip()
        elif lower.startswith("notbefore="):
            result["not_before"] = stripped.split("=", 1)[1].strip()
        elif lower.startswith("notafter="):
            result["not_after"] = stripped.split("=", 1)[1].strip()
        elif "fingerprint=" in lower:
            result["sha256_fingerprint"] = stripped.split("=", 1)[1].strip()
    return result


def collect_tls_metadata(cert_paths: Sequence[Path], *, runner=run_command) -> dict:
    observed_at = _utc_now()
    certificates: list[dict] = []
    for raw_path in cert_paths:
        path = Path(raw_path)
        if _PRIVATE_KEY_PATH_HINT.search(path.name):
            certificates.append({"path": str(path), "status": "rejected", "reason": "private_key_candidate"})
            continue
        obs = runner([
            "/usr/bin/openssl", "x509", "-in", str(path), "-noout",
            "-subject", "-issuer", "-serial", "-dates", "-fingerprint", "-sha256",
        ])
        if obs.status != "ok":
            certificates.append({"path": str(path), "status": "inconclusive", "reason": obs.status})
            continue
        certificates.append({"path": str(path), "status": "ok", "reason": None, **_parse_openssl_metadata(obs.stdout)})
    available = any(item.get("status") == "ok" for item in certificates)
    return {"available": available, "status": "ok" if available else "inconclusive", "observed_at": observed_at, "certificates": certificates}


def collect_vault_prerequisites(*, runner=run_command, vault_binary: str | None = None) -> dict:
    observed_at = _utc_now()
    target = {
        "product": "HashiCorp Vault",
        "edition": "community",
        "version": "1.21.4",
        "deployment": "single_node_lab",
        "storage": "integrated_storage_raft",
        "tls_required": True,
    }
    if vault_binary:
        vault_obs = runner([vault_binary, "version"])
        vault = {
            "status": "present" if vault_obs.status == "ok" else "inconclusive",
            "version_text": vault_obs.stdout.strip() if vault_obs.status == "ok" else None,
            "reason": None if vault_obs.status == "ok" else vault_obs.status,
        }
    else:
        vault = {"status": "not_observed", "version_text": None, "reason": "binary_path_not_supplied"}

    docker_obs = runner(["/usr/bin/docker", "version", "--format", "{{.Server.Version}}"])
    docker = {
        "status": "present" if docker_obs.status == "ok" else "inconclusive",
        "server_version": docker_obs.stdout.strip() if docker_obs.status == "ok" else None,
        "reason": None if docker_obs.status == "ok" else docker_obs.status,
    }
    return {
        "observed_at": observed_at,
        "target": target,
        "observed": {"vault": vault, "docker": docker},
        "mutation_performed": False,
    }


def collect_recovery_constraints() -> dict:
    return {
        "source": "repository_target_design",
        "runtime_observed": False,
        "storage": "integrated_storage_raft_single_node_lab",
        "unseal": {"mechanism": "shamir", "shares": 3, "threshold": 2, "material_boundary": "outside_hermes"},
        "root": {"initial_token": "bootstrap_only", "persistent_root_allowed": False, "revoke_before_operational_acceptance": True},
        "snapshot": {"required": True, "independent_copy_required": True, "restore_drill_required": True},
    }
