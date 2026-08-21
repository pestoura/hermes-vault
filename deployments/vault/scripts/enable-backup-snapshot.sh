#!/usr/bin/env bash
# Operator-run JIT provisioning of the dedicated scheduled snapshot AppRole.
set -euo pipefail

[[ "${VAULT_BACKUP_OPERATOR_ACK:-}" == "yes" ]] || {
  echo "HITL REFUSES: set VAULT_BACKUP_OPERATOR_ACK=yes" >&2
  exit 1
}
: "${VAULT_TOKEN:?JIT token with vault-admin-policy + vault-admin-auth is required}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${DEPLOY_DIR}/../.." && pwd)"
COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.yml"
POLICY="${REPO_ROOT}/policies/backup/vault-backup-snapshot.hcl"

vault() {
  docker compose -f "${COMPOSE_FILE}" --project-directory "${DEPLOY_DIR}" \
    exec -T -e VAULT_TOKEN vault vault "$@"
}

cleanup() {
  vault token revoke -self >/dev/null 2>&1 || true
}
trap cleanup EXIT

[[ -f "${POLICY}" ]] || { echo "backup policy missing" >&2; exit 2; }
cat "${POLICY}" | vault policy write vault-backup-snapshot -

if ! vault auth list -format=json | grep -q '"approle/"'; then
  vault auth enable approle
fi

vault write auth/approle/role/vault-backup \
  bind_secret_id=true \
  token_policies=vault-backup-snapshot \
  token_no_default_policy=true \
  token_ttl=5m \
  token_max_ttl=5m \
  token_explicit_max_ttl=5m \
  token_num_uses=2 \
  token_type=service \
  secret_id_num_uses=40 \
  secret_id_ttl=840h

ROLE_ID="$(vault read -field=role_id auth/approle/role/vault-backup/role-id)"
[[ -n "${ROLE_ID}" ]] || { echo "backup RoleID missing" >&2; exit 3; }
printf 'VAULT_BACKUP_ROLE_ID=%s\n' "${ROLE_ID}"
echo "VAULT_BACKUP_APPROLE_PROVISION_PASS"
