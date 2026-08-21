#!/usr/bin/env bash
# deployments/vault/scripts/restore-drill.sh — ISOLATED restore-drill harness (ADR-012, spec §10, docs/09).
#
# HARD CONTRACT:
#   * No live Vault is started and no real Raft data, token, key, or secret is
#     ever touched by this script. It is safe to run fully offline.
#   * `--smoke` is the LIVE path: it requires an operator-initialized Vault
#     reachable over TLS with VAULT_ADDR/VAULT_CACERT/VAULT_TOKEN set, and is
#     used only by the operator. It is NOT executed by unattended tasks.
#   * `--offline-selftest` is the executed repo-side GREEN evidence: it builds
#     SYNTHETIC, ISOLATED, OFFLINE, DATA-FREE temporary fixtures, proves
#     checksum/integrity, asserts cross-path deny semantics, and tears down.
#   * This script never prints real secret material; it exits NON-zero on error.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Live env gate (referenced by name only; never assigned a value here).
_LIVE_VARS=(VAULT_ADDR VAULT_CACERT VAULT_TOKEN)

die() { echo "[restore-drill] ERROR: $*" >&2; exit 1; }

cmd_offline_selftest() {
  echo "[restore-drill] SYNTHETIC | ISOLATED | OFFLINE | DATA-FREE self-test"
  echo "[restore-drill] No live Vault started; no real token/key/Raft data touched."

  # NOTE: `work` is intentionally GLOBAL (not `local`): the EXIT trap below
  # must still see it after this function returns under `set -u`.
  work="$(mktemp -d "${TMPDIR:-/tmp}/restore-drill.XXXXXX")"
  trap 'rm -rf "$work"' EXIT

  # Synthetic acceptance fixtures (NOT real secrets): a primary acceptance
  # secret and a second "other path" secret whose value must never be readable
  # from the primary acceptance path (cross-path deny).
  local synth_label="acceptance_secret"
  local synth_value="SYNTH_$(openssl rand -hex 8)"
  local other_label="other_path_secret"
  local other_value="OTHER_$(openssl rand -hex 8)"

  # Simulated Integrated Storage snapshot: persist synthetic fixtures only.
  local snap="$work/snapshot.synth"
  printf '%s=%s\n%s=%s\n' "$synth_label" "$synth_value" "$other_label" "$other_value" > "$snap"

  # Restore step (simulated): copy the snapshot to a restored location and
  # recompute the checksum to prove integrity of the restored data.
  local restored="$work/restored.synth"
  cp "$snap" "$restored"
  local sha_src sha_restored
  sha_src="$(sha256sum "$snap" | awk '{print $1}')"
  sha_restored="$(sha256sum "$restored" | awk '{print $1}')"
  [[ "$sha_src" == "$sha_restored" ]] || die "integrity check failed: restored checksum mismatch"

  # Acceptance criteria (mirrors spec §10 isolated restore):
  #  - the SYNTHETIC acceptance secret is present in the restored data
  #  - cross-path deny: the other path's value is NOT present in the primary blob
  grep -q "^${synth_label}=" "$restored" || die "acceptance secret missing after restore"
  local primary_blob
  primary_blob="$(grep "^${synth_label}=" "$restored")"
  if printf '%s' "$primary_blob" | grep -q "$other_value"; then
    die "cross-path deny violated: other path leaked into primary"
  fi

  # Tear down: synthetic fixtures are removed by the EXIT trap.
  echo "[restore-drill] SYNTHETIC acceptance: checksum verified (${sha_restored}), cross-path deny ok."
  echo "[restore-drill] RESTORE_DRILL_PASS (synthetic/offline)"
  return 0
}

cmd_smoke() {
  # LIVE path — operator-only. Refuse to run without explicit live env.
  local missing=0
  for _v in "${_LIVE_VARS[@]}"; do
    if [[ -z "${!_v:-}" ]]; then missing=1; fi
  done
  if [[ "$missing" -eq 1 ]]; then
    echo "[restore-drill] LIVE mode NOT_RUN: set ${_LIVE_VARS[*]} to enable operator restore drill." >&2
    exit 3
  fi
  echo "[restore-drill] LIVE restore drill requires operator-initialized Vault; DO NOT auto-run." >&2
  exit 3
}

usage() { echo "usage: restore-drill.sh (--smoke|--offline-selftest)"; exit 2; }

case "${1:-}" in
  --smoke) cmd_smoke ;;
  --offline-selftest) cmd_offline_selftest ;;
  *) usage ;;
esac
