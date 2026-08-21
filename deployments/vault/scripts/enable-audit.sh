#!/usr/bin/env bash
# Operator-only (HITL) enable of the mandatory Vault file audit device.
# Uses the exact Vault CLI from the running pinned container, never a host CLI.
set -euo pipefail

if [[ "${VAULT_AUDIT_OPERATOR_ACK:-}" != "yes" ]]; then
  echo "HITL REFUSES: enabling audit is operator-only." >&2
  echo "Set VAULT_AUDIT_OPERATOR_ACK=yes in the operator shell to proceed." >&2
  exit 1
fi
: "${VAULT_TOKEN:?operator token must already exist in the operator shell}"
command -v docker >/dev/null 2>&1 || { echo "docker is required" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.yml"

vault() {
  docker compose -f "${COMPOSE_FILE}" --project-directory "${DEPLOY_DIR}" \
    exec -T -e VAULT_TOKEN vault vault "$@"
}

AUDIT_PATH="${VAULT_AUDIT_FILE_PATH:-/vault/logs/audit.json}"
if vault audit list -format=json 2>/dev/null | grep -q '"file/"'; then
  echo "audit device 'file/' already enabled — skipping (idempotent)."
  exit 0
fi

vault audit enable file file_path="${AUDIT_PATH}"
echo "audit device enabled: file file_path=${AUDIT_PATH}"
echo "STATUS: applied by operator (HITL)."
