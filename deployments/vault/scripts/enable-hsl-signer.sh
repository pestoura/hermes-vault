#!/usr/bin/env bash
#
# enable-hsl-signer.sh — Operator-only (HITL) creation of the HSL signer AppRole
# bound to the exact-path `hsl-signer` policy (Task E2, spec §11.2-§11.3, ADR-014).
#
# Creates exactly ONE AppRole `hsl-signer` bound to exactly ONE policy
# `hsl-signer` (policies/hsl/hsl-signer.hcl). The AppRole grants ONLY the
# contract's sign/verify/read capabilities on hsl-transit/hsl-signing; no
# wildcard, no sudo, no shared-secret access, no cross-consumer mounts (spec §11.3).
# The script is IDEMPOTENT: if the `hsl-signer` AppRole already exists it skips
# re-creation (Vault errors on a conflicting duplicate write).
#
# CONTRACT SCOPE (shared ownership, spec §3/§15/§17):
#   * hermes-vault owns deployment/lifecycle. This script is the provider-owned
#     AppRole bootstrap artifact. HSL (pestoura/hermes-security-labs) does NOT
#     own or modify this deployment; it only consumes the hsl-signer AppRole via
#     the published contract (Task M1, cross-repo onboarding specified, not performed).
#
# HARD BOUNDARY (never in unattended tasks / CI):
#   * This script does NOT start Vault.
#   * It does NOT perform operator init / unseal / root handling.
#   * It does NOT generate, read, print, or transmit any role secret, token,
#     key, or recovery material. Issuing a role secret is an operator HITL step
#     recorded in runbooks, never coded or auto-executed here. The operator
#     supplies VAULT_ADDR/VAULT_CACERT and an already-issued operator token in
#     their OWN shell; this script only ensures the AppRole auth method is enabled
#     and invokes `vault write auth/approle/...` to create the AppRole binding.
#   * It refuses to run unattended (no VAULT_HSL_SIGNER_OPERATOR_ACK).
#
# Operator bootstrap sequence (HITL, recorded in runbooks — NOT auto-executed):
#   1. vault policy write hsl-signer policies/hsl/hsl-signer.hcl   (apply the committed policy)
#   2. ./enable-hsl-signer.sh                                       (this script: bind AppRole -> policy)
#   3. Issue a role secret for the HSL consumer out-of-band (HITL) — never here.
set -euo pipefail

# HITL guard: refuse unattended execution. Operator must acknowledge out-of-band.
if [[ "${VAULT_HSL_SIGNER_OPERATOR_ACK:-}" != "yes" ]]; then
  echo "HITL REFUSES: creating the hsl-signer AppRole is an operator-only step." >&2
  echo "Set VAULT_HSL_SIGNER_OPERATOR_ACK=yes in your operator shell to proceed." >&2
  exit 1
fi

# Operator-supplied environment (set in the operator's own shell, never here):
#   VAULT_ADDR     e.g. https://127.0.0.1:8200
#   VAULT_CACERT   path to the CA cert used for TLS verification
#   VAULT_TOKEN    an already-issued operator token (NEVER printed/read by this script)
command -v vault >/dev/null 2>&1 || { echo "vault CLI is required" >&2; exit 1; }

# Provider-owned AppRole + policy names. The contract is the contract.
APPROLE_NAME="hsl-signer"
POLICY_NAME="hsl-signer"

# Token TTLs (spec §11.3 least-privilege lease): short-lived signer token.
TOKEN_TTL="15m"
TOKEN_MAX_TTL="1h"

# CIDR binding — applied ONLY when the operator provides a stable CIDR. Left
# empty by default; not yet stable in this environment (controller guardrail:
# "CIDR when stable").
CIDR_BIND="${VAULT_HSL_SIGNER_CIDR:-}"

# --- 1) AppRole auth method (idempotent) ------------------------------------
if vault auth list -format=json 2>/dev/null | grep -q '"approle/"'; then
  echo "auth method 'approle/' already enabled — skipping (idempotent)."
else
  vault auth enable approle
  echo "auth method enabled: approle/"
fi

# --- 2) AppRole (idempotent) ------------------------------------------------
if vault read "auth/approle/role/${APPROLE_NAME}" -format=json >/dev/null 2>&1; then
  echo "approle '${APPROLE_NAME}' already present — skipping (idempotent)."
else
  # Create the AppRole bound to the exact-path hsl-signer policy only.
  # token_policies binds the least-privilege policy; no token_global, no sudo,
  # no cross-consumer access. Issuing a role secret is operator HITL (NOT here).
  if [[ -n "${CIDR_BIND}" ]]; then
    vault write "auth/approle/role/${APPROLE_NAME}" \
      token_policies="${POLICY_NAME}" \
      token_ttl="${TOKEN_TTL}" \
      token_max_ttl="${TOKEN_MAX_TTL}" \
      token_bound_cidrs="${CIDR_BIND}"
  else
    vault write "auth/approle/role/${APPROLE_NAME}" \
      token_policies="${POLICY_NAME}" \
      token_ttl="${TOKEN_TTL}" \
      token_max_ttl="${TOKEN_MAX_TTL}"
  fi
  echo "approle created: auth/approle/role/${APPROLE_NAME} (policy=${POLICY_NAME})"
fi

echo "STATUS: applied by operator (HITL). Live verification is operator responsibility."
echo "NOTE: role-secret issuance/wrapping is an operator HITL step (NOT performed here)."
