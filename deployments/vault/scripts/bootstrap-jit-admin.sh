#!/usr/bin/env bash
# ADR-022 operator-only bootstrap of certificate-authenticated JIT administration.
# Requires an already-unsealed Vault, an active file audit device, an operator
# token already present in the operator shell, and a PUBLIC client certificate.
# It never logs in with the client certificate and never revokes the bootstrap token.
set -euo pipefail

if [[ "${VAULT_JIT_ADMIN_OPERATOR_ACK:-}" != "yes" ]]; then
  echo "HITL REFUSES: set VAULT_JIT_ADMIN_OPERATOR_ACK=yes in the operator shell." >&2
  exit 1
fi

: "${VAULT_ADDR:?VAULT_ADDR is required}"
: "${VAULT_CACERT:?VAULT_CACERT is required}"
: "${VAULT_TOKEN:?operator token must already exist in the operator shell}"
: "${VAULT_ADMIN_CERT_PEM:?path to the PUBLIC client certificate PEM is required}"

command -v vault >/dev/null 2>&1 || { echo "vault CLI is required" >&2; exit 1; }
command -v openssl >/dev/null 2>&1 || { echo "openssl is required" >&2; exit 1; }
[[ -f "${VAULT_ADMIN_CERT_PEM}" ]] || { echo "public certificate file not found" >&2; exit 1; }

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

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
POLICY_DIR="${REPO_ROOT}/policies/admin"

vault policy write vault-admin-issuer "${POLICY_DIR}/vault-admin-issuer.hcl"
vault policy write vault-admin-policy "${POLICY_DIR}/vault-admin-policy.hcl"
vault policy write vault-admin-auth "${POLICY_DIR}/vault-admin-auth.hcl"
vault policy write vault-admin-token "${POLICY_DIR}/vault-admin-token.hcl"
vault policy write vault-admin-secrets-engine "${POLICY_DIR}/vault-admin-secrets-engine.hcl"
vault policy write vault-admin-audit "${POLICY_DIR}/vault-admin-audit.hcl"

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

vault write auth/cert/certs/vault-admin-issuer \
  display_name=vault-admin-issuer \
  "certificate=@${VAULT_ADMIN_CERT_PEM}" \
  token_policies=vault-admin-issuer \
  token_ttl=5m \
  token_max_ttl=5m \
  token_explicit_max_ttl=5m \
  token_no_default_policy=true \
  token_num_uses=0 \
  token_type=service

echo "ADR-022 bootstrap objects applied. Root revocation is NOT performed here."
echo "Next gate: independent certificate login + JIT-token positive/negative capability proof."
