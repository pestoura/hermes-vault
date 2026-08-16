#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)
ROLES_JSON="$REPO_ROOT/identity/workload-roles.json"
POLICY_DIR="$REPO_ROOT/identity/policies"
MATRIX_JSON="$REPO_ROOT/identity/negative-capability-matrix.json"
EXPECTED_VAULT_VERSION="Vault v1.21.4"

fail() {
  printf 'EPIC-02 refused: %s\n' "$*" >&2
  exit 1
}

role_allowed() {
  case "${1:-}" in
    hermes-runtime|hermes-controller|jarvas-operations|github-tool) return 0 ;;
    *) return 1 ;;
  esac
}

preflight() {
  command -v vault >/dev/null 2>&1 || fail "vault CLI is required"
  command -v python3 >/dev/null 2>&1 || fail "python3 is required"
  [[ "${VAULT_ADDR:-}" == https://* ]] || fail "VAULT_ADDR must use https://"
  [[ -z "${VAULT_SKIP_VERIFY:-}" ]] || fail "VAULT_SKIP_VERIFY must be unset"
  [[ -n "${VAULT_CACERT:-}" && -r "$VAULT_CACERT" ]] || fail "VAULT_CACERT must be readable"
  local version
  version=$(vault version 2>/dev/null || true)
  [[ "$version" == "$EXPECTED_VAULT_VERSION"* ]] || fail "vault CLI must be version 1.21.4"
  python3 "$REPO_ROOT/tools/validate_identity_contract.py" "$ROLES_JSON" >/dev/null
  python3 "$REPO_ROOT/tools/lint_vault_policies.py" "$POLICY_DIR" >/dev/null
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
' || fail "current Vault token is not the controlled bootstrap root credential"
}

require_approle() {
  vault auth list -format=json | python3 -c '
import json, sys
obj = json.load(sys.stdin)
entry = obj.get("approle/")
raise SystemExit(0 if isinstance(entry, dict) and entry.get("type") == "approle" else 1)
' || fail "AppRole auth method is not enabled at approle/"
}

kv_probe() {
  vault secrets list -detailed -format=json | python3 -c '
import json, sys
obj = json.load(sys.stdin)
entry = obj.get("secret/")
if entry is None:
    raise SystemExit(3)
opts = entry.get("options") or {}
if entry.get("type") != "kv" or str(opts.get("version")) != "2":
    raise SystemExit(4)
raise SystemExit(0)
'
}

kv_status() {
  require_unsealed
  require_initial_root
  local rc=0
  kv_probe >/dev/null 2>&1 || rc=$?
  case "$rc" in
    0) printf '%s\n' "EPIC02_KV_V2_EXACT" ;;
    3) printf '%s\n' "EPIC02_KV_ABSENT" ;;
    4) printf '%s\n' "EPIC02_KV_DIVERGENT"; return 4 ;;
    *) fail "unable to evaluate secret/ mount" ;;
  esac
}

kv_enable() {
  require_unsealed
  require_initial_root
  local rc=0
  kv_probe >/dev/null 2>&1 || rc=$?
  case "$rc" in
    0)
      printf '%s\n' "EPIC02_KV_ALREADY_EXACT"
      return 0
      ;;
    3)
      vault secrets enable -path=secret -version=2 kv >/dev/null
      ;;
    4)
      fail "existing secret/ mount is not the approved KV v2 mount"
      ;;
    *)
      fail "unable to evaluate secret/ mount"
      ;;
  esac
  kv_probe >/dev/null || fail "secret/ did not converge to KV v2"
  printf '%s\n' "EPIC02_KV_V2_ENABLED"
}

configure_policies() {
  require_unsealed
  require_initial_root
  local policy
  for policy in hermes-runtime hermes-controller jarvas-operations github-tool; do
    vault policy write "$policy" "$POLICY_DIR/$policy.hcl" >/dev/null
  done
  printf '%s\n' "EPIC02_POLICIES_CONFIGURED"
}

configure_roles() {
  require_unsealed
  require_initial_root
  require_approle
  while IFS=$'\t' read -r role policy ttl max_ttl; do
    vault write "auth/approle/role/$role" \
      token_policies="$policy" \
      token_no_default_policy=true \
      token_ttl="$ttl" \
      token_max_ttl="$max_ttl" \
      secret_id_num_uses=1 \
      secret_id_ttl=10m >/dev/null
  done < <(python3 - "$ROLES_JSON" <<'PY'
import json, sys
obj = json.load(open(sys.argv[1], encoding="utf-8"))
for name in sorted(obj["roles"]):
    role = obj["roles"][name]
    print(name, role["policy"], role["token_ttl"], role["token_max_ttl"], sep="\t")
PY
)
  printf '%s\n' "EPIC02_APPROLES_CONFIGURED"
}

role_id() {
  local role=${1:-}
  role_allowed "$role" || fail "unknown role"
  require_unsealed
  require_initial_root
  require_approle
  vault read -field=role_id "auth/approle/role/$role/role-id"
}

wrapped_secret_id() {
  local role=${1:-}
  role_allowed "$role" || fail "unknown role"
  require_unsealed
  require_initial_root
  require_approle
  # Output is a response-wrapped SecretID envelope. Treat stdout as credential material.
  vault write -wrap-ttl=5m -f "auth/approle/role/$role/secret-id"
}

require_current_policy() {
  local role=${1:-}
  vault token lookup -format=json | python3 -c '
import json, sys
expected = sys.argv[1]
obj = json.load(sys.stdin)
policies = set((obj.get("data") or {}).get("policies") or [])
raise SystemExit(0 if policies == {expected} else 1)
' "$role" || fail "current Vault token must contain exactly the policy for $role"
}

capability_check() {
  local role=${1:-}
  role_allowed "$role" || fail "unknown role"
  require_unsealed
  require_current_policy "$role"

  python3 - "$MATRIX_JSON" "$role" <<'PY' | while IFS=$'\t' read -r kind path expected; do
import json, sys
obj = json.load(open(sys.argv[1], encoding="utf-8"))
role = sys.argv[2]
entry = obj["identities"][role]
for kind in ("positive", "negative"):
    for item in entry[kind]:
        print(kind, item["path"], ",".join(sorted(item["expected"])), sep="\t")
PY
    local_json=$(vault token capabilities -format=json "$path")
    actual=$(python3 -c '
import json, sys
obj=json.load(sys.stdin)
if isinstance(obj, list): caps=obj
elif isinstance(obj, dict): caps=obj.get("capabilities") or next((v for v in obj.values() if isinstance(v, list)), [])
else: caps=[]
print(",".join(sorted(str(x) for x in caps)))
' <<<"$local_json")
    [[ "$actual" == "$expected" ]] || fail "$role $kind capability mismatch on $path: expected=$expected actual=$actual"
  done
  printf 'EPIC02_CAPABILITY_MATRIX_PASS role=%s\n' "$role"
}

usage() {
  cat >&2 <<'EOF'
Usage: epic02_identity_kv.sh <command> [role]

Commands:
  preflight
  kv-status
  kv-enable
  configure-policies
  configure-roles
  role-id ROLE
  wrapped-secret-id ROLE
  capability-check ROLE

`role-id` and `wrapped-secret-id` are bootstrap provisioning actions.
`capability-check` uses the current Vault token; never pass a token as an argument.
This script never writes a KV secret value, migrates a credential, rotates a provider
credential, or removes a legacy secret.
EOF
  exit 2
}

main() {
  preflight
  case "${1:-}" in
    preflight) printf '%s\n' "EPIC02_PREFLIGHT_OK" ;;
    kv-status) kv_status ;;
    kv-enable) kv_enable ;;
    configure-policies) configure_policies ;;
    configure-roles) configure_roles ;;
    role-id) role_id "${2:-}" ;;
    wrapped-secret-id) wrapped_secret_id "${2:-}" ;;
    capability-check) capability_check "${2:-}" ;;
    *) usage ;;
  esac
}

main "$@"
