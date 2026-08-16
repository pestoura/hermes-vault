#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)
BACKUP_POLICY="$REPO_ROOT/baseline/policies/lab-l1-backup.hcl"
EXPECTED_VAULT_VERSION="Vault v1.21.4"
AUDIT_PATH="lab-l1-file/"
AUDIT_FILE="/vault/audit/audit.log"

fail() {
  printf 'EPIC-01 refused: %s\n' "$*" >&2
  exit 1
}

preflight() {
  command -v vault >/dev/null 2>&1 || fail "vault CLI is required"
  command -v python3 >/dev/null 2>&1 || fail "python3 is required"
  command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required"
  command -v realpath >/dev/null 2>&1 || fail "realpath is required"
  command -v mktemp >/dev/null 2>&1 || fail "mktemp is required"

  [[ "${VAULT_ADDR:-}" == https://* ]] || fail "VAULT_ADDR must use https://"
  [[ -z "${VAULT_SKIP_VERIFY:-}" ]] || fail "VAULT_SKIP_VERIFY must be unset"
  [[ -n "${VAULT_CACERT:-}" ]] || fail "VAULT_CACERT must be configured"
  [[ -r "$VAULT_CACERT" ]] || fail "VAULT_CACERT is not readable"

  local version
  version=$(vault version 2>/dev/null || true)
  [[ "$version" == "$EXPECTED_VAULT_VERSION"* ]] || fail "vault CLI must be version 1.21.4"
}

require_unsealed() {
  local rc=0
  vault status >/dev/null 2>&1 || rc=$?
  [[ "$rc" -eq 0 ]] || fail "Vault must be initialized and unsealed"
}

require_initial_root() {
  vault token lookup -format=json | python3 -c '
import json, sys
obj = json.load(sys.stdin)
policies = set((obj.get("data") or {}).get("policies") or [])
raise SystemExit(0 if "root" in policies else 1)
' || fail "current credential is not the bootstrap root credential"
}

audit_probe() {
  vault audit list -format=json | python3 -c '
import json, sys
obj = json.load(sys.stdin)
entry = obj.get("lab-l1-file/")
if entry is None:
    raise SystemExit(3)
opts = entry.get("options") or {}
expected = {
    "file_path": "/vault/audit/audit.log",
    "format": "json",
    "hmac_accessor": "true",
    "log_raw": "false",
    "elide_list_responses": "true",
    "mode": "0600",
}
if entry.get("type") != "file":
    raise SystemExit(4)
for key, value in expected.items():
    observed = str(opts.get(key, "")).lower()
    if observed != value.lower():
        raise SystemExit(4)
raise SystemExit(0)
'
}

audit_status() {
  require_unsealed
  local rc=0
  audit_probe >/dev/null 2>&1 || rc=$?
  case "$rc" in
    0) printf '%s\n' "LAB_L1_AUDIT_EXACT" ;;
    3) printf '%s\n' "LAB_L1_AUDIT_ABSENT" ;;
    4) printf '%s\n' "LAB_L1_AUDIT_DIVERGENT"; return 4 ;;
    *) fail "unable to evaluate audit device" ;;
  esac
}

audit_enable() {
  require_unsealed
  require_initial_root
  local rc=0
  audit_probe >/dev/null 2>&1 || rc=$?
  case "$rc" in
    0)
      printf '%s\n' "LAB_L1_AUDIT_ALREADY_EXACT"
      return 0
      ;;
    3)
      ;;
    4)
      fail "existing lab-l1-file audit device has divergent configuration"
      ;;
    *)
      fail "unable to evaluate existing audit devices"
      ;;
  esac

  vault audit enable \
    -path=lab-l1-file \
    file \
    file_path=/vault/audit/audit.log \
    mode=0600 \
    format=json \
    hmac_accessor=true \
    log_raw=false \
    elide_list_responses=true >/dev/null

  audit_probe >/dev/null || fail "audit device did not converge to the expected configuration"
  printf '%s\n' "LAB_L1_AUDIT_ENABLED"
}

backup_role_configure() {
  require_unsealed
  require_initial_root
  [[ -r "$BACKUP_POLICY" ]] || fail "backup policy file is missing"

  vault policy write hermes-lab-l1-backup "$BACKUP_POLICY" >/dev/null
  vault write auth/approle/role/hermes-lab-l1-backup \
    token_policies=hermes-lab-l1-backup \
    token_no_default_policy=true \
    token_ttl=10m \
    token_max_ttl=30m \
    secret_id_num_uses=1 \
    secret_id_ttl=10m >/dev/null
  printf '%s\n' "LAB_L1_BACKUP_ROLE_CONFIGURED"
}

backup_role_id() {
  require_unsealed
  require_initial_root
  vault read -field=role_id auth/approle/role/hermes-lab-l1-backup/role-id
}

backup_wrapped_secret_id() {
  require_unsealed
  require_initial_root
  vault write -wrap-ttl=5m -f auth/approle/role/hermes-lab-l1-backup/secret-id
}

snapshot_path() {
  local requested=${1:-}
  [[ -n "$requested" ]] || fail "snapshot path is required"
  local resolved
  resolved=$(realpath -m -- "$requested")
  [[ "$resolved" == /* ]] || fail "snapshot path must resolve to an absolute path"
  case "$resolved" in
    "$REPO_ROOT"|"$REPO_ROOT"/*)
      fail "snapshot must not be stored in the repository"
      ;;
    /vault/data|/vault/data/*|/vault/audit|/vault/audit/*)
      fail "snapshot must not be stored in Vault Raft or audit storage"
      ;;
  esac
  printf '%s\n' "$resolved"
}

snapshot_save() {
  require_unsealed
  local output
  output=$(snapshot_path "${1:-}")
  local parent tmpdir tmpfile sidecar hash
  parent=$(dirname -- "$output")
  install -d -m 700 -- "$parent"
  umask 077
  tmpdir=$(mktemp -d "${parent}/.hermes-vault-snapshot.XXXXXX")
  trap 'rm -rf -- "$tmpdir"' EXIT
  tmpfile="$tmpdir/snapshot.snap"
  sidecar="$tmpdir/snapshot.sha256"

  vault operator raft snapshot save "$tmpfile"
  vault operator raft snapshot inspect "$tmpfile" >/dev/null
  hash=$(sha256sum -- "$tmpfile" | awk '{print $1}')
  printf '%s  %s\n' "$hash" "$(basename -- "$output")" >"$sidecar"
  chmod 0600 -- "$tmpfile" "$sidecar"
  mv -- "$tmpfile" "$output"
  mv -- "$sidecar" "${output}.sha256"
  rmdir -- "$tmpdir"
  trap - EXIT
  printf 'LAB_L1_SNAPSHOT_SAVED sha256=%s path=%s\n' "$hash" "$output"
}

snapshot_inspect() {
  local snapshot
  snapshot=$(snapshot_path "${1:-}")
  [[ -r "$snapshot" ]] || fail "snapshot file is not readable"
  if [[ -r "${snapshot}.sha256" ]]; then
    local expected actual
    expected=$(awk 'NR==1 {print $1}' "${snapshot}.sha256")
    actual=$(sha256sum -- "$snapshot" | awk '{print $1}')
    [[ -n "$expected" && "$expected" == "$actual" ]] || fail "snapshot SHA-256 sidecar mismatch"
  fi
  vault operator raft snapshot inspect "$snapshot"
}

usage() {
  cat >&2 <<'EOF'
Usage: lab_l1_baseline.sh <command> [argument]

Commands:
  preflight
  audit-status
  audit-enable
  backup-role-configure
  backup-role-id
  backup-wrapped-secret-id
  snapshot-save ABSOLUTE_OUTPUT.snap
  snapshot-inspect SNAPSHOT.snap

This script never restores a snapshot and never accepts Shamir shares, root tokens,
SecretIDs, wrapping tokens or Vault client tokens as command-line arguments.
EOF
  exit 2
}

main() {
  preflight
  case "${1:-}" in
    preflight) printf '%s\n' "LAB_L1_BASELINE_PREFLIGHT_OK" ;;
    audit-status) audit_status ;;
    audit-enable) audit_enable ;;
    backup-role-configure) backup_role_configure ;;
    backup-role-id) backup_role_id ;;
    backup-wrapped-secret-id) backup_wrapped_secret_id ;;
    snapshot-save) snapshot_save "${2:-}" ;;
    snapshot-inspect) snapshot_inspect "${2:-}" ;;
    *) usage ;;
  esac
}

main "$@"
