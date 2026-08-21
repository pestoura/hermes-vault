from __future__ import annotations

import json
from pathlib import Path

from tools.phase0_collectors import (
    SYSTEM_UNITS,
    USER_UNITS,
    collect_docker,
    collect_host,
    collect_listeners,
    collect_storage,
    collect_systemd,
)
from tools.phase0_contract import REPORT_SCHEMA, build_report, collect_phase0_report, evaluate_phase0
from tools.phase0_core import (
    DEFAULT_TIMEOUT_S,
    MAX_CAPTURE_BYTES,
    CommandObservation,
    run_command,
    sanitize_text,
    write_report_atomic,
)
from tools.phase0_prerequisites import collect_recovery_constraints, collect_tls_metadata, collect_vault_prerequisites
from tools.phase0_references import classify_reference, collect_secret_references

__all__ = [
    "DEFAULT_TIMEOUT_S", "MAX_CAPTURE_BYTES", "REPORT_SCHEMA", "SYSTEM_UNITS", "USER_UNITS",
    "CommandObservation", "build_report", "classify_reference", "collect_docker", "collect_host",
    "collect_listeners", "collect_phase0_report", "collect_recovery_constraints", "collect_secret_references",
    "collect_storage", "collect_systemd", "collect_tls_metadata", "collect_vault_prerequisites", "evaluate_phase0",
    "run_command", "sanitize_text", "write_report_atomic",
]


def _cli() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Read-only Hermes Vault Phase 0 discovery")
    parser.add_argument("--output", type=Path, help="Write sanitized JSON report atomically with mode 0600")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print sanitized report to stdout")
    parser.add_argument("--reference-path", action="append", type=Path, dest="reference_paths")
    parser.add_argument("--cert-path", action="append", type=Path, dest="cert_paths")
    parser.add_argument("--vault-binary", help="Observed Vault CLI path; no Vault mutation is performed")
    args = parser.parse_args()

    kwargs = {"cert_paths": tuple(args.cert_paths or ()), "vault_binary": args.vault_binary}
    if args.reference_paths:
        kwargs["reference_paths"] = tuple(args.reference_paths)
    report = collect_phase0_report(**kwargs)
    if args.output:
        write_report_atomic(args.output, report)
    if args.pretty or not args.output:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["gates"]["DISCOVERY_COMPLETE"]["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(_cli())
