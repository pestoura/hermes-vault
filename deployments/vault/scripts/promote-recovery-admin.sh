#!/usr/bin/env bash
# ADR-023 operator-only promotion of the recovery JIT class into an existing live Vault.
set -euo pipefail

if [[ "${VAULT_RECOVERY_PROMOTION_OPERATOR_ACK:-}" != "yes" ]]; then
  echo "HITL REFUSES: set VAULT_RECOVERY_PROMOTION_OPERATOR_ACK=yes in the operator shell." >&2
  exit 1
fi

: "${VAULT_TOKEN:?operator JIT token must already exist in the operator shell}"
command -v docker >/dev/null 2>&1 || { echo "docker is required" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 is required" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${DEPLOY_DIR}/../.." && pwd)"
COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.yml"
POLICY_DIR="${REPO_ROOT}/policies/admin"

vault() {
  docker compose -f "${COMPOSE_FILE}" --project-directory "${DEPLOY_DIR}" \
    exec -T -e VAULT_TOKEN vault vault "$@"
}

# The promotion token must itself be short-lived JIT, never root/default.
vault token lookup -format=json | python3 -c '
import json,sys
x=json.load(sys.stdin)["data"]
p=set(x.get("policies", []))
required={"vault-admin-policy","vault-admin-token"}
assert required <= p, p
assert "root" not in p and "default" not in p, p
assert x.get("renewable") is False
assert x.get("orphan") is True
assert 0 < int(x.get("ttl", 0)) <= 600
'
cat "${POLICY_DIR}/vault-admin-recovery.hcl" | vault policy write vault-admin-recovery -

vault write auth/token/roles/hermes-vault-admin \
  allowed_policies=vault-admin-policy,vault-admin-auth,vault-admin-token,vault-admin-secrets-engine,vault-admin-audit,vault-admin-recovery,vault-admin-hsl-bootstrap \
  disallowed_policies=default,root \
  orphan=true \
  renewable=false \
  token_no_default_policy=true \
  token_explicit_max_ttl=10m \
  token_type=service

echo "ADR023_RECOVERY_PROMOTION_PASS"
echo "Next gate: mint a JIT token requesting only vault-admin-recovery for live fixture staging."
