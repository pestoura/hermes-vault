#!/usr/bin/env bash
# deployments/vault/scripts/snapshot.sh — LIVE Integrated Storage snapshot (ADR-012, spec §10, docs/09).
#
# HARD CONTRACT:
#   * This script performs `vault operator raft snapshot save` against a LIVE,
#     operator-initialized Vault. It MUST NOT be invoked by any unattended task
#     or CI. It is an operator/HITL step only.
#   * It writes the snapshot + checksum/metadata into the git-ignored `backups/`
#     directory so runtime copies never reach the repository.
#   * It never prints real secret material (tokens, keys, shares). It exits
#     NON-zero on any error (fail-closed).
#
# This script is intentionally NOT executed by Task D1 (controller guardrail:
# do NOT snapshot/restore a live Vault). It is committed as the production
# artifact; its existence, scope, and data-free source are validated offline.
set -euo pipefail

BACKUP_DIR="${VAULT_BACKUP_DIR:-backups}"
RETENTION="${VAULT_SNAPSHOT_RETENTION:-14}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
SNAP="${BACKUP_DIR}/vault-raft-${TS}.snapshot"
META="${SNAP}.meta.json"
ENC="${SNAP}.enc"

echo "[snapshot] LIVE mode — requires an operator-initialized Vault."
echo "[snapshot] target backup dir: ${BACKUP_DIR} (git-ignored)"

# Guard: refuse to run if not pointed at a live Vault. The live endpoint is
# provided out-of-band by the operator; an empty/localhost-default without a
# real token must NOT be silently "successful".
if [[ -z "${VAULT_ADDR:-}" || -z "${VAULT_TOKEN:-}" ]]; then
  echo "[snapshot] ABORT: VAULT_ADDR and VAULT_TOKEN must be set by the operator (live target)." >&2
  exit 3
fi

mkdir -p "${BACKUP_DIR}"

# 1) Save the Integrated Storage snapshot.
echo "[snapshot] saving raft snapshot -> ${SNAP}"
vault operator raft snapshot save "${SNAP}"

# 2) Checksum + metadata (no secret values, only sizes/hashes).
SIZE=$(stat -c '%s' "${SNAP}")
SHA=$(sha256sum "${SNAP}" | awk '{print $1}')
cat > "${META}" <<EOF
{
  "artifact": "vault.raft.snapshot",
  "mode": "live",
  "captured_at_utc": "${TS}",
  "vault_addr": "${VAULT_ADDR}",
  "snapshot_file": "$(basename "${SNAP}")",
  "size_bytes": ${SIZE},
  "sha256": "${SHA}"
}
EOF
echo "[snapshot] meta -> ${META}"

# 3) Independent encrypted copy (AES-256-CBC via openssl). The passphrase is
#    supplied by the operator out-of-band; it is NEVER embedded here. If absent,
#    we still keep the checksum'd local copy but refuse to emit an unencrypted
#    independent copy claim.
if [[ -n "${VAULT_SNAPSHOT_PASSPHRASE:-}" ]]; then
  openssl enc -aes-256-cbc -salt -pbkdf2 \
    -in "${SNAP}" -out "${ENC}" -pass env:VAULT_SNAPSHOT_PASSPHRASE
  ENC_SHA=$(sha256sum "${ENC}" | awk '{print $1}')
  echo "[snapshot] encrypted independent copy -> ${ENC} (sha256 ${ENC_SHA})"
else
  echo "[snapshot] no VAULT_SNAPSHOT_PASSPHRASE set — encrypted independent copy SKIPPED (local checksum'd copy kept)."
fi

# 4) Retention: prune oldest local snapshots beyond RETENTION.
if command -v ls >/dev/null 2>&1; then
  ls -1t "${BACKUP_DIR}"/vault-raft-*.snapshot 2>/dev/null \
    | tail -n +"$((RETENTION + 1))" \
    | xargs -r rm -f || true
fi

echo "[snapshot] DONE — snapshot captured and checksummed (live)."
