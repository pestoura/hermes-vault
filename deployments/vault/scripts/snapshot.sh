#!/usr/bin/env bash
# LIVE Raft snapshot capture for ADR-012 / ADR-023.
# Operator-only: strict loopback TLS, no host Vault CLI, no secret output.
set -euo pipefail

CANONICAL_ADDR="https://127.0.0.1:8200"
BACKUP_DIR="${VAULT_BACKUP_DIR:-backups}"
RETENTION="${VAULT_SNAPSHOT_RETENTION:-14}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
SNAP="${BACKUP_DIR}/vault-raft-${TS}.snapshot"
TMP="${SNAP}.partial.$$"
META="${SNAP}.meta.json"
ENC="${SNAP}.enc"
ENC_TMP="${ENC}.partial.$$"

fail() { echo "[snapshot] ABORT: $*" >&2; exit 3; }

[[ "${VAULT_SNAPSHOT_OPERATOR_ACK:-}" == "yes" ]] || \
  fail "operator acknowledgement required"
for required in VAULT_ADDR VAULT_CACERT VAULT_TOKEN VAULT_SNAPSHOT_PASSPHRASE; do
  [[ -n "${!required:-}" ]] || fail "${required} is required"
done
[[ "${VAULT_ADDR}" == "${CANONICAL_ADDR}" ]] || \
  fail "VAULT_ADDR must be canonical loopback TLS endpoint"
[[ -f "${VAULT_CACERT}" ]] || fail "VAULT_CACERT is not a file"

umask 077
mkdir -p "${BACKUP_DIR}"
chmod 700 "${BACKUP_DIR}"
cleanup_on_exit() {
  rc=$?
  trap - EXIT
  rm -f -- "${TMP}" "${ENC_TMP}" "${META}.tmp"
  if [[ "${rc}" -ne 0 ]]; then
    rm -f -- "${SNAP}" "${SNAP}.sha256" "${META}" \
      "${ENC}" "${ENC}.sha256"
  fi
  exit "${rc}"
}
trap cleanup_on_exit EXIT

echo "[snapshot] capturing Raft snapshot over strict loopback TLS"
python3 - "${TMP}" "${SNAP}" <<'PY'
import os
import ssl
import sys
import urllib.request

out_path = sys.argv[1]
final_path = sys.argv[2]
addr = os.environ["VAULT_ADDR"]
ca = os.environ["VAULT_CACERT"]
token = os.environ["VAULT_TOKEN"]
ctx = ssl.create_default_context(cafile=ca)
req = urllib.request.Request(
    addr + "/v1/sys/storage/raft/snapshot",
    method="GET",
    headers={"X-Vault-Token": token},
)
fd = os.open(out_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
try:
    with os.fdopen(fd, "wb") as dst:
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            if resp.status != 200:
                raise RuntimeError(f"snapshot HTTP status {resp.status}")
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)
        dst.flush()
        os.fsync(dst.fileno())
    os.replace(out_path, final_path)
except Exception:
    try:
        os.unlink(out_path)
    except FileNotFoundError:
        pass
    raise
PY
chmod 600 "${SNAP}"
SIZE="$(stat -c '%s' "${SNAP}")"
SHA="$(sha256sum "${SNAP}" | awk '{print $1}')"
printf '%s  %s\n' "${SHA}" "$(basename "${SNAP}")" > "${SNAP}.sha256"
chmod 600 "${SNAP}.sha256"

openssl enc -aes-256-cbc -salt -pbkdf2 \
  -in "${SNAP}" -out "${ENC_TMP}" -pass env:VAULT_SNAPSHOT_PASSPHRASE
chmod 600 "${ENC_TMP}"
mv "${ENC_TMP}" "${ENC}"
ENC_SHA="$(sha256sum "${ENC}" | awk '{print $1}')"
printf '%s  %s\n' "${ENC_SHA}" "$(basename "${ENC}")" > "${ENC}.sha256"
chmod 600 "${ENC}" "${ENC}.sha256"

python3 - "${META}.tmp" "${TS}" "$(basename "${SNAP}")" \
  "${SIZE}" "${SHA}" "$(basename "${ENC}")" "${ENC_SHA}" <<'PY'
import json
import os
import sys

out, captured, snap, size, sha, enc, enc_sha = sys.argv[1:]
data = {
    "artifact": "vault.raft.snapshot",
    "mode": "live",
    "captured_at_utc": captured,
    "vault_addr": "https://127.0.0.1:8200",
    "snapshot_file": snap,
    "size_bytes": int(size),
    "sha256": sha,
    "encrypted_file": enc,
    "encrypted_sha256": enc_sha,
}
with open(out, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2, sort_keys=True)
    fh.write("\n")
os.chmod(out, 0o600)
PY
mv "${META}.tmp" "${META}"
chmod 600 "${META}"

# Bounded retention: remove each old snapshot and its exact companions together.
mapfile -t OLD < <(ls -1t "${BACKUP_DIR}"/vault-raft-*.snapshot 2>/dev/null | tail -n +"$((RETENTION + 1))")
for old in "${OLD[@]:-}"; do
  [[ -n "${old}" ]] || continue
  rm -f -- "${old}" "${old}.sha256" "${old}.meta.json" \
    "${old}.enc" "${old}.enc.sha256"
done

trap - EXIT
echo "[snapshot] DONE — snapshot, checksums and encrypted copy captured"
