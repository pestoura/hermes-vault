#!/usr/bin/env bash
#
# enable-hsl-transit.sh — Operator-only (HITL) enable of the HSL-dedicated
# Transit secrets engine + signing key for the Hermes Shared Vault Service
# (Task E1, spec §13, ADR-014).
#
# Enables exactly ONE Transit mount at path `hsl-transit` and creates exactly
# ONE key `hsl-signing` (the HSL consumer contract, spec §13). The script is
# IDEMPOTENT: if `hsl-transit/` is already mounted it skips re-enable, and if
# `hsl-signing` already exists it skips re-creation (Vault errors on duplicate
# enable / duplicate key creation).
#
# CONTRACT SCOPE (shared ownership, spec §3/§15/§17):
#   * `hermes-vault` owns this deployment/lifecycle. This script is the
#     provider-owned enable artifact. HSL (pestoura/hermes-security-labs) does
#     NOT own or modify this deployment; it only consumes the `hsl-transit/`
#     mount + `hsl-signing` key via the published contract (Task M1, cross-repo
#     onboarding is specified, not performed here).
#
# HARD BOUNDARY (never in unattended tasks / CI):
#   * This script does NOT start Vault.
#   * It does NOT perform operator init / unseal / root handling.
#   * It does NOT read, print, or transmit any token, key, or recovery
#     material. The operator supplies VAULT_ADDR/VAULT_CACERT and an
#     already-issued operator token in their OWN shell; this script only invokes
#     `vault secrets enable` and `vault write hsl-transit/keys/...`.
#   * It refuses to run unattended (no VAULT_HSL_TRANSIT_OPERATOR_ACK).
#
# The HSL `deployment/vault-lab-l1` transit pattern is generalized here into the
# shared service; the `hsl-transit/` mount + `hsl-signing` key are dedicated to
# the HSL consumer and provider-owned by hermes-vault.
set -euo pipefail

# HITL guard: refuse unattended execution. Operator must acknowledge out-of-band.
if [[ "${VAULT_HSL_TRANSIT_OPERATOR_ACK:-}" != "yes" ]]; then
  echo "HITL REFUSES: enabling the HSL Transit mount/key is an operator-only step." >&2
  echo "Set VAULT_HSL_TRANSIT_OPERATOR_ACK=yes in your operator shell to proceed." >&2
  exit 1
fi

# Operator supplies only the already-issued JIT token in the local shell.
# The pinned Vault container provides VAULT_ADDR/VAULT_CACERT and the exact CLI.
# VAULT_TOKEN is passed into that container process and is never printed here.
command -v docker >/dev/null 2>&1 || { echo "docker is required" >&2; exit 1; }
[[ -n "${VAULT_TOKEN:-}" ]] || { echo "VAULT_TOKEN must exist in the operator shell" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.yml"

vault() {
  docker compose -f "${COMPOSE_FILE}" --project-directory "${DEPLOY_DIR}" \
    exec -T -e VAULT_TOKEN vault vault "$@"
}

# HSL dedicated Transit contract (spec §13): fixed, dedicated mount + key names.
# These are provider-owned by hermes-vault and consumed by HSL; they are not
# configurable — the contract is the contract.
MOUNT_PATH="hsl-transit"
KEY_NAME="hsl-signing"

# --- 1) Transit mount (idempotent) -------------------------------------------
if vault secrets list -format=json 2>/dev/null | grep -q "\"hsl-transit/\"";
then
  echo "transit mount 'hsl-transit/' already enabled — skipping (idempotent)."
else
  vault secrets enable -path=hsl-transit transit
  echo "transit mount enabled: hsl-transit/"
fi

# --- 2) HSL signing key (idempotent) ------------------------------------------
if vault read "hsl-transit/keys/hsl-signing" -format=json >/dev/null 2>&1; then
  echo "transit key 'hsl-signing' already present — skipping (idempotent)."
else
  # HSL dedicated signing key. `type=ed25519` provides a modern signing
  # primitive suitable for HSL evidence/transit signing (spec §13).
  vault write hsl-transit/keys/hsl-signing type=ed25519
  echo "transit key created: hsl-transit/keys/hsl-signing (type=ed25519)"
fi

echo "STATUS: applied by operator (HITL). Live verification is operator responsibility."
