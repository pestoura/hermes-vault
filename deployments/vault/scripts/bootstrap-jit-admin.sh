#!/usr/bin/env bash
# ADR-022 operator-only bootstrap of certificate-authenticated JIT administration.
# Uses the Vault CLI from the exact pinned runtime container; no host Vault CLI.
# Requires active file audit, an operator token already present in the operator
# shell, and a PUBLIC dedicated ClientAuth leaf certificate.
set -euo pipefail

if [[ "${VAULT_JIT_ADMIN_OPERATOR_ACK:-}" != "yes" ]]; then
  echo "HITL REFUSES: set VAULT_JIT_ADMIN_OPERATOR_ACK=yes in the operator shell." >&2
  exit 1
fi

: "${VAULT_TOKEN:?operator token must already exist in the operator shell}"
: "${VAULT_ADMIN_CERT_PEM:?path to the PUBLIC client certificate PEM is required}"

command -v docker >/dev/null 2>&1 || { echo "docker is required" >&2; exit 1; }
command -v openssl >/dev/null 2>&1 || { echo "openssl is required" >&2; exit 1; }
[[ -f "${VAULT_ADMIN_CERT_PEM}" ]] || { echo "public certificate file not found" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${DEPLOY_DIR}/../.." && pwd)"
COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.yml"
POLICY_DIR="${REPO_ROOT}/policies/admin"

vault() {
  docker compose -f "${COMPOSE_FILE}" --project-directory "${DEPLOY_DIR}" \
    exec -T -e VAULT_TOKEN vault vault "$@"
}

openssl x509 -in "${VAULT_ADMIN_CERT_PEM}" -noout >/dev/null 2>&1 || {
  echo "certificate validation failed: expected an X.509 public certificate" >&2
  exit 1
}
CERT_TEXT="$(openssl x509 -in "${VAULT_ADMIN_CERT_PEM}" -noout -text)"
if grep -q 'CA:TRUE' <<<"${CERT_TEXT}"; then
  echo "certificate validation failed: dedicated client leaf certificate required" >&2
  exit 1
fi
if ! grep -q 'TLS Web Client Authentication' <<<"${CERT_TEXT}"; then
  echo "certificate validation failed: ClientAuth EKU required" >&2
  exit 1
fi

AUDIT_JSON="$(vault audit list -format=json 2>/dev/null || true)"
if ! grep -q '"file/"' <<<"${AUDIT_JSON}"; then
  echo "AUDIT_REQUIRED: file/ audit device must be enabled before ADR-022 bootstrap." >&2
  exit 2
fi

cat "${POLICY_DIR}/vault-admin-issuer.hcl" | vault policy write vault-admin-issuer -
cat "${POLICY_DIR}/vault-admin-policy.hcl" | vault policy write vault-admin-policy -
cat "${POLICY_DIR}/vault-admin-auth.hcl" | vault policy write vault-admin-auth -
cat "${POLICY_DIR}/vault-admin-token.hcl" | vault policy write vault-admin-token -
cat "${POLICY_DIR}/vault-admin-secrets-engine.hcl" | vault policy write vault-admin-secrets-engine -
cat "${POLICY_DIR}/vault-admin-audit.hcl" | vault policy write vault-admin-audit -

if ! vault auth list -format=json | grep -q '"cert/"'; then
  vault auth enable cert
fi

vault write auth/token/roles/hermes-vault-admin \
  allowed_policies=vault-admin-policy,vault-admin-auth,vault-admin-token,vault-admin-secrets-engine,vault-admin-audit \
  disallowed_policies=default,root \
  orphan=true \
  renewable=false \
  token_no_default_policy=true \
  token_explicit_max_ttl=10m \
  token_type=service

cat "${VAULT_ADMIN_CERT_PEM}" | vault write auth/cert/certs/vault-admin-issuer \
  display_name=vault-admin-issuer \
  certificate=- \
  token_policies=vault-admin-issuer \
  token_ttl=5m \
  token_max_ttl=5m \
  token_explicit_max_ttl=5m \
  token_no_default_policy=true \
  token_num_uses=0 \
  token_type=service

echo "ADR-022 bootstrap objects applied. Root revocation is NOT performed here."
echo "Next gate: independent certificate login + JIT-token positive/negative capability proof."
