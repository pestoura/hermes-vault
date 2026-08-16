#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VAULT_VERSION="Vault v1.21.4"

fail() {
  printf 'EPIC-01 restore drill refused: %s\n' "$*" >&2
  exit 1
}

plan() {
  cat <<'EOF'
LAB_L1_RESTORE_DRILL_PLAN
1. Use a separately initialized scratch Vault with isolated storage and network.
2. Do not reuse the LAB_L1 Raft volume, audit volume, listener publication or client network.
3. Copy the selected snapshot into scratch custody and verify its SHA-256 sidecar.
4. Set HERMES_VAULT_RESTORE_SCOPE=ISOLATED_SCRATCH.
5. Set HERMES_VAULT_RESTORE_NETWORK_ISOLATION_CONFIRMED=YES only after isolation is verified.
6. Set HERMES_VAULT_RESTORE_STORAGE_ISOLATED=YES only after scratch storage is verified independent.
7. Point VAULT_ADDR/VAULT_CACERT at the scratch instance only.
8. Run this script with preflight SNAPSHOT.snap.
9. The actual force restore remains a separate HITL operator action; this script never performs it.
10. After restore, use the original cluster Shamir custody process to unseal and validate the isolated instance.
EOF
}

require_scratch_address() {
  [[ "${VAULT_ADDR:-}" == https://* ]] || fail "scratch VAULT_ADDR must use https://"
  case "$VAULT_ADDR" in
    https://127.0.0.1:18200|https://localhost:18200|https://vault:8200|https://vault:8200/)
      fail "the canonical LAB_L1 address is forbidden for restore drill preflight"
      ;;
  esac
}

preflight() {
  local snapshot=${1:-}
  [[ -n "$snapshot" ]] || fail "snapshot path is required"
  [[ "${HERMES_VAULT_RESTORE_SCOPE:-}" == "ISOLATED_SCRATCH" ]] || fail "HERMES_VAULT_RESTORE_SCOPE must be ISOLATED_SCRATCH"
  [[ "${HERMES_VAULT_RESTORE_NETWORK_ISOLATION_CONFIRMED:-}" == "YES" ]] || fail "network isolation has not been confirmed"
  [[ "${HERMES_VAULT_RESTORE_STORAGE_ISOLATED:-}" == "YES" ]] || fail "scratch storage isolation has not been confirmed"
  require_scratch_address
  [[ -z "${VAULT_SKIP_VERIFY:-}" ]] || fail "VAULT_SKIP_VERIFY must be unset"
  [[ -n "${VAULT_CACERT:-}" && -r "$VAULT_CACERT" ]] || fail "scratch VAULT_CACERT must be readable"
  [[ -r "$snapshot" ]] || fail "snapshot is not readable"

  command -v vault >/dev/null 2>&1 || fail "vault CLI is required"
  command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required"
  local version
  version=$(vault version 2>/dev/null || true)
  [[ "$version" == "$EXPECTED_VAULT_VERSION"* ]] || fail "vault CLI must be version 1.21.4"

  if [[ -r "${snapshot}.sha256" ]]; then
    local expected actual
    expected=$(awk 'NR==1 {print $1}' "${snapshot}.sha256")
    actual=$(sha256sum -- "$snapshot" | awk '{print $1}')
    [[ -n "$expected" && "$expected" == "$actual" ]] || fail "snapshot SHA-256 sidecar mismatch"
  fi

  vault operator raft snapshot inspect "$snapshot" >/dev/null

  local rc=0
  vault status >/dev/null 2>&1 || rc=$?
  [[ "$rc" -eq 0 ]] || fail "scratch Vault must be initialized, online and unsealed before the HITL restore"

  printf '%s\n' "LAB_L1_ISOLATED_RESTORE_PREFLIGHT_PASS"
  printf '%s\n' "No restore was executed. Continue only through the governed HITL procedure."
}

usage() {
  printf 'Usage: restore_drill.sh <plan|preflight SNAPSHOT.snap>\n' >&2
  exit 2
}

case "${1:-}" in
  plan) plan ;;
  preflight) preflight "${2:-}" ;;
  *) usage ;;
esac
