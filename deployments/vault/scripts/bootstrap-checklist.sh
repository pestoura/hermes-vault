#!/usr/bin/env bash
#
# bootstrap-checklist.sh — READ-ONLY checklist printer for the Hermes Vault
# init/unseal/root bootstrap (Task B4, spec §8, §9, ADR-002).
#
# This script does NOT perform any secret-related operation. It ONLY prints the
# operator checklist so a human can execute the HITL steps out-of-band.
#
# HARD BOUNDARY (never in unattended tasks):
#   vault operator init
#   vault operator unseal
#   initial root token handling / revoke
#   AppRole SecretID issuance / wrapping
#   TLS private-key generation / custody
#
# This printer MUST NOT start Vault, run init/unseal, read or write tokens,
# shares, keys, or SecretIDs, or generate TLS material. It is documentation as
# code — a fail-closed guardrail, not an executor.
set -euo pipefail

cat <<'EOF'
================================================================
 Hermes Vault — BOOTSTRAP CHECKLIST (READ-ONLY / PRINTER ONLY)
================================================================

 STATUS: NOT_RUN
 All live steps below are HITL (operator-only) and NOT executed
 by this script, CI, or any unattended task.

----------------------------------------------------------------
 [0] PRECONDITIONS (operator)
----------------------------------------------------------------
  [ ] Pinned image running (HSL digest, 1.21.4):
      hashicorp/vault:1.21.4@sha256:4e33b126a59c0c333b76fb4e894722462659a6bec7c48c9ee8cea56fccfd2569
  [ ] TLS listener up (B3, operator-only provisioning)
  [ ] VAULT_ADDR / VAULT_CACERT set in operator shell
  [ ] Quorum of >= 2 credentialed operators present

----------------------------------------------------------------
 [1] INIT  (HITL — operator-only; DO NOT AUTOMATE)
----------------------------------------------------------------
  [ ] Run by operator out-of-band:
        vault operator init -key-shares=3 -key-threshold=2
  [ ] Capture 3 unseal keys + initial root token FROM TERMINAL OUTPUT
  [ ] Record to OUT-OF-BAND CUSTODY immediately
  [ ] Confirm nothing written to repo / logs / CI / evidence bundle

----------------------------------------------------------------
 [2] UNSEAL — QUORUM  (HITL — operator-only, x2)
----------------------------------------------------------------
  [ ] Operator A:  vault operator unseal <UNSEAL_KEY_1>
  [ ] Operator B:  vault operator unseal <UNSEAL_KEY_2>
  [ ] Confirm Vault is unsealed (threshold reached)

----------------------------------------------------------------
 [3] REVOKE INITIAL ROOT  (HITL — operator-only)
----------------------------------------------------------------
  [ ] After admin identity/policy in place, operator runs out-of-band:
        vault token revoke <INITIAL_ROOT_TOKEN>
  [ ] Confirm root token no longer usable

----------------------------------------------------------------
 [4] ENABLE AUDIT  (HITL — operator-only)
----------------------------------------------------------------
  [ ] vault audit enable file file_path=/vault/logs/audit.log

----------------------------------------------------------------
 REMINDER: this printer performs NO secret operations.
 Live init / unseal / root / SecretID / TLS-key remain
 operator-only and OUT OF SCOPE of any automated run.
================================================================
EOF

echo "[checklist] printed operator bootstrap checklist (read-only). No secret operation performed."
