#!/usr/bin/env bash
#
# enable-audit.sh — Operator-only (HITL) enable of the mandatory file audit
# device for the Hermes Shared Vault Service (Task C1, ADR-011, spec §9/§21.2).
#
# Enables exactly ONE audit device of type `file` writing to
# /vault/logs/audit.json, and is IDEMPOTENT: if the file device is already
# enabled it skips re-enable (Vault errors on duplicate enable).
#
# HARD BOUNDARY (never in unattended tasks / CI):
#   * This script does NOT start Vault.
#   * It does NOT perform operator init / unseal / root handling.
#   * It does NOT read, print, or transmit any token, key, or recovery
#     material. The operator supplies VAULT_ADDR/VAULT_CACERT and an
#     already-issued operator token in their OWN shell; this script only invokes
#     `vault audit enable` with the device parameters.
#   * It refuses to run unattended (no VAULT_AUDIT_OPERATOR_ACK).
#
# Redaction of audit output is enforced by Vault's audit system plus the
# consumer redaction layer (src/evidence/redact.py, G2). This script only
# enables the device; it never reads audit contents.
set -euo pipefail

# HITL guard: refuse unattended execution. Operator must acknowledge out-of-band.
if [[ "${VAULT_AUDIT_OPERATOR_ACK:-}" != "yes" ]]; then
  echo "HITL REFUSES: enabling audit is an operator-only step. Set" >&2
  echo "VAULT_AUDIT_OPERATOR_ACK=yes in your operator shell to proceed." >&2
  exit 1
fi

# Operator-supplied environment (set in the operator's own shell, never here):
#   VAULT_ADDR   e.g. https://127.0.0.1:8200
#   VAULT_CACERT path to the CA cert used for TLS verification
#   VAULT_TOKEN  an already-issued operator token (NEVER printed/read by this script)
command -v vault >/dev/null 2>&1 || { echo "vault CLI is required" >&2; exit 1; }

AUDIT_PATH="${VAULT_AUDIT_FILE_PATH:-/vault/logs/audit.json}"

# Idempotency: list enabled devices; if a `file` device is already present, skip.
if vault audit list -format=json 2>/dev/null | grep -q '"file/":'; then
  echo "audit device 'file/' already enabled — skipping (idempotent)."
  exit 0
fi

vault audit enable file file_path="${AUDIT_PATH}"
echo "audit device enabled: file file_path=${AUDIT_PATH}"
echo "STATUS: applied by operator (HITL). Live verification is operator responsibility."
