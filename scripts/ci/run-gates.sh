#!/usr/bin/env bash
# scripts/ci/run-gates.sh — local PRIMARY gate runner (GitHub billing aborts Actions ~2s).
# Fail-CLOSED: any real gate failure stops the run non-zero. Never emits secrets;
# never touches Vault runtime.
set -euo pipefail

DRY=0
SCAN_ONLY=0
case "${1:-}" in
  --dry)       DRY=1 ;;
  --scan-only) SCAN_ONLY=1 ;;
  "")          : ;;
  *) echo "usage: run-gates.sh [--dry|--scan-only]" >&2; exit 2 ;;
esac

# Suites that are planned-but-not-yet-populated. pytest rc=5 ("no tests
# collected") is tolerated ONLY for these; every other suite must have tests.
# Controller ruling: rc=5 is the ONLY tolerated non-zero pytest outcome.
FUTURE_EMPTY_GATES=" tests/lifecycle tests/evidence tests/secret_zero tests/isolation tests/audit tests/recovery "

# run_gate <label> <target...> — fail-closed pytest wrapper.
#   rc=0        -> PASS
#   rc=5        -> EMPTY, tolerated only if EVERY target is a named future-empty
#                  suite; otherwise hard failure
#   rc=1,2,3,4  -> propagate non-zero and stop the gate
run_gate() {
  local label="$1"; shift
  local targets=("$@")
  echo "[gate] ${label}"
  local rc=0
  pytest "${targets[@]}" -q || rc=$?
  if [ "$rc" -eq 0 ]; then
    return 0
  fi
  if [ "$rc" -eq 5 ]; then
    local t allowed=1
    for t in "${targets[@]}"; do
      case "$FUTURE_EMPTY_GATES" in
        *" $t "*) : ;;
        *) allowed=0 ;;
      esac
    done
    if [ "$allowed" -eq 1 ]; then
      echo "[gate] ${label}: no tests collected (rc=5) — tolerated future-empty suite"
      return 0
    fi
    echo "[gate] ${label}: FAIL — rc=5 not allowed for populated suite" >&2
    exit 5
  fi
  echo "[gate] ${label}: FAIL — pytest rc=${rc}" >&2
  exit "$rc"
}

# secret_scan — scan the TRACKED tree only (git ls-files excludes gitignored /
# untracked / runtime material). Detects `hvs.`-prefixed tokens and the legacy
# `s.`/assignment shapes. NEVER prints a matched value: only redacted text and
# the offending file path.
secret_scan() {
  echo "[gate] secret-scan"
  local pattern='(hvs\.[A-Za-z0-9]{20,})|(s\.[A-Za-z0-9]{20,})|((VAULT_TOKEN|VAULT_[A-Z0-9]+|[Rr]oot_token|recovery_key|SecretID)[[:space:]]*[:=][[:space:]]*[A-Za-z0-9._-]{16,})'
  # Restrict to the meaningful roots but keep it broad: repo root, .github,
  # scripts, docs, policies, src, templates, and tests. The latter is explicit
  # (not merely inherited from ':(top)*') so the FUTURE-proof contract holds:
  # secret-shaped test fixtures are NOT scanner-blind. Design prose in the
  # plan/ledger docs (docs/superpowers/) merely names controls and is excluded.
  local hit_files=()
  local f
  local tracked
  tracked=$(git ls-files -- \
              ':(top)*' \
              ':(top).github/**' \
              ':(top)scripts/**' \
              ':(top)docs/**' \
              ':(top)policies/**' \
              ':(top)src/**' \
              ':(top)templates/**' \
              ':(top)tests/**' 2>/dev/null) || tracked=""
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    case "$f" in
      docs/superpowers/*) continue ;;
    esac
    if LC_ALL=C grep -Eq "$pattern" -- "$f" 2>/dev/null; then
      hit_files+=("$f")
    fi
  done <<< "$tracked"

  if [ "${#hit_files[@]}" -gt 0 ]; then
    echo "SECRET PATTERN FOUND — redacted; matched value not shown" >&2
    for f in "${hit_files[@]}"; do
      echo "  offending file: ${f}" >&2
    done
    exit 1
  fi
  echo "clean"
}

# --- fast gates (cheap, deterministic, Vault-free) ---
run_fast_gates() {
  run_gate "policy-lint"          tests/policy_lint
  run_gate "contract-schema"      tests/contract
  run_gate "lifecycle/invariants" tests/lifecycle tests/evidence
  run_gate "secret-zero"          tests/secret_zero
}

if [ "$SCAN_ONLY" = 1 ]; then
  secret_scan
  exit 0
fi

run_fast_gates

if [ "$DRY" = 1 ]; then
  echo "[gate] dry run ok"
  exit 0
fi

# Full mode only (operator, local): secret scan + HITL-gated integration suites.
secret_scan

run_gate "integration (requires local HITL Vault)" tests/isolation tests/audit tests/recovery
