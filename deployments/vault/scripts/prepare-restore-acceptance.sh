#!/usr/bin/env bash
# ADR-023 operator-only staging of synthetic recovery fixtures on the live Vault.
# Requires a JIT token carrying only vault-admin-recovery.
set -euo pipefail

[[ "${VAULT_RESTORE_STAGE_OPERATOR_ACK:-}" == "yes" ]] || {
  echo "HITL REFUSES: operator acknowledgement required" >&2
  exit 1
}
for required in VAULT_ADDR VAULT_CACERT VAULT_TOKEN VAULT_SNAPSHOT_PASSPHRASE; do
  [[ -n "${!required:-}" ]] || {
    echo "HITL REFUSES: ${required} is required" >&2
    exit 1
  }
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${DEPLOY_DIR}/../.." && pwd)"
COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.yml"
RUN_ROOT="${VAULT_RESTORE_RUN_ROOT:-${REPO_ROOT}/backups/restore-runs}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="${RUN_ROOT}/adr023-${TS}-$$"
CERT="${RUN_DIR}/restore-acceptance.pem"
KEY="${RUN_DIR}/restore-acceptance.key"
LIVE_DIRTY=0

vault() {
  docker compose -f "${COMPOSE_FILE}" --project-directory "${DEPLOY_DIR}" \
    exec -T -e VAULT_TOKEN vault vault "$@"
}
cleanup_live() {
  local rc=0
  vault delete auth/cert/certs/restore-acceptance >/dev/null 2>&1 || rc=1
  vault policy delete restore-acceptance-test >/dev/null 2>&1 || rc=1
  vault secrets disable restore-acceptance-kv >/dev/null 2>&1 || rc=1
  vault secrets disable restore-acceptance-transit >/dev/null 2>&1 || rc=1
  LIVE_DIRTY=0
  return "${rc}"
}

cleanup_on_exit() {
  local main_rc=$?
  local cleanup_rc=0
  trap - EXIT
  if [[ "${LIVE_DIRTY}" -eq 1 ]]; then
    cleanup_live || cleanup_rc=$?
  fi
  vault token revoke -self >/dev/null 2>&1 || true
  if [[ "${main_rc}" -ne 0 || "${cleanup_rc}" -ne 0 ]]; then
    rm -rf -- "${RUN_DIR}"
    exit 1
  fi
  exit 0
}

umask 077
mkdir -p "${RUN_DIR}"
chmod 700 "${RUN_DIR}"
trap cleanup_on_exit EXIT

openssl req -x509 -newkey rsa:2048 -sha256 -days 1 -nodes \
  -keyout "${KEY}" -out "${CERT}" \
  -subj "/CN=restore-acceptance" \
  -addext "basicConstraints=critical,CA:FALSE" \
  -addext "keyUsage=critical,digitalSignature,keyEncipherment" \
  -addext "extendedKeyUsage=clientAuth" >/dev/null 2>&1
chmod 600 "${KEY}" "${CERT}"
vault secrets enable -path=restore-acceptance-kv kv-v2 >/dev/null
LIVE_DIRTY=1
vault secrets enable -path=restore-acceptance-transit transit >/dev/null

vault kv put restore-acceptance-kv/primary marker=ADR023_PRIMARY_OK >/dev/null
vault kv put restore-acceptance-kv/forbidden marker=ADR023_FORBIDDEN_OK >/dev/null
vault write -f restore-acceptance-transit/keys/restore-acceptance >/dev/null

cat "${REPO_ROOT}/policies/recovery/restore-acceptance-test.hcl" | \
  vault policy write restore-acceptance-test - >/dev/null
cat "${CERT}" | vault write auth/cert/certs/restore-acceptance \
  display_name=restore-acceptance \
  certificate=- \
  token_policies=restore-acceptance-test \
  token_ttl=5m \
  token_max_ttl=5m \
  token_explicit_max_ttl=5m \
  token_no_default_policy=true \
  token_type=service >/dev/null

echo "[restore-stage] synthetic fixtures staged; capturing snapshot"
export VAULT_BACKUP_DIR="${RUN_DIR}"
export VAULT_SNAPSHOT_OPERATOR_ACK=yes
bash "${SCRIPT_DIR}/snapshot.sh"
unset VAULT_SNAPSHOT_OPERATOR_ACK VAULT_BACKUP_DIR

cleanup_live
vault token revoke -self >/dev/null
unset VAULT_TOKEN
trap - EXIT

echo "ADR023_RESTORE_STAGE_PASS"
echo "ADR023_RUN_DIR=${RUN_DIR}"
