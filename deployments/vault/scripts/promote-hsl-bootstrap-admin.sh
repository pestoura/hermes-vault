#!/usr/bin/env bash
# Operator-only, fail-closed promotion of the exact HSL bootstrap JIT class
# into a live post-root Vault. No production/consumer promotion is performed.
# Run twice with separate class-scoped JIT tokens: policy, then role.
set -euo pipefail

if [[ "${VAULT_HSL_BOOTSTRAP_PROMOTION_OPERATOR_ACK:-}" != "yes" ]]; then
  echo "HITL REFUSES: set VAULT_HSL_BOOTSTRAP_PROMOTION_OPERATOR_ACK=yes." >&2
  exit 1
fi

: "${VAULT_TOKEN:?operator JIT token must already exist in the operator shell}"
command -v docker >/dev/null 2>&1 || { echo "docker is required" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 is required" >&2; exit 1; }

MODE="${1:-}"
case "${MODE}" in
  "policy") EXPECTED_POLICY="vault-admin-policy" ;;
  "role") EXPECTED_POLICY="vault-admin-token" ;;
  *) echo "usage: $0 {policy|role}" >&2; exit 2 ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${DEPLOY_DIR}/../.." && pwd)"
COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.yml"
POLICY_DIR="${REPO_ROOT}/policies/admin"

vault() {
  docker compose -f "${COMPOSE_FILE}" --project-directory "${DEPLOY_DIR}" \
    exec -T -e VAULT_TOKEN vault vault "$@"
}

# Require exactly one expected JIT class, never root/default or a combined token.
vault token lookup -format=json | python3 -c '
import json,sys
x=json.load(sys.stdin)["data"]
expected=sys.argv[1]
p=set(x.get("policies", []))
assert p == {expected}, p
assert "root" not in p and "default" not in p, p
assert x.get("renewable") is False
assert x.get("orphan") is True
assert 0 < int(x.get("ttl", 0)) <= 600
' "${EXPECTED_POLICY}"

case "${MODE}" in
  "policy")
    cat "${POLICY_DIR}/vault-admin-hsl-bootstrap.hcl" | \
      vault policy write vault-admin-hsl-bootstrap -
    ;;
  "role")
    vault write auth/token/roles/hermes-vault-admin \
      allowed_policies=vault-admin-policy,vault-admin-auth,vault-admin-token,vault-admin-secrets-engine,vault-admin-audit,vault-admin-recovery,vault-admin-hsl-bootstrap \
      disallowed_policies=default,root \
      orphan=true \
      renewable=false \
      token_no_default_policy=true \
      token_explicit_max_ttl=10m \
      token_type=service
    ;;
esac

# Every promotion token retires itself immediately after its one bounded action.
vault token revoke -self
echo "HSL_BOOTSTRAP_JIT_PROMOTION_PASS mode=${MODE} token=self-revoked"
