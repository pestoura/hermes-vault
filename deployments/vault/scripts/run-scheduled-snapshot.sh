#!/usr/bin/env bash
# Runtime loader for user-scoped encrypted snapshot credentials.
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_BASE="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
SECRET_BLOB="${HOME}/.config/credstore.encrypted/hermes-vault-backup-secret-id"
PASSPHRASE_BLOB="${HOME}/.config/credstore.encrypted/hermes-vault-snapshot-passphrase"

[[ -d "${RUNTIME_BASE}" ]] || {
  echo "SCHEDULED_SNAPSHOT_FAIL reason=runtime_dir_missing" >&2
  exit 3
}
[[ -r "${SECRET_BLOB}" && -r "${PASSPHRASE_BLOB}" ]] || {
  echo "SCHEDULED_SNAPSHOT_FAIL reason=encrypted_credentials_missing" >&2
  exit 3
}

RUNTIME_CREDS="$(mktemp -d "${RUNTIME_BASE}/hermes-vault-snapshot.XXXXXX")"
chmod 700 "${RUNTIME_CREDS}"
cleanup() {
  rm -rf -- "${RUNTIME_CREDS}"
}
trap cleanup EXIT
systemd-creds --user --name=backup-secret-id decrypt \
  "${SECRET_BLOB}" "${RUNTIME_CREDS}/backup-secret-id" >/dev/null
systemd-creds --user --name=snapshot-passphrase decrypt \
  "${PASSPHRASE_BLOB}" "${RUNTIME_CREDS}/snapshot-passphrase" >/dev/null
chmod 600 "${RUNTIME_CREDS}/backup-secret-id" "${RUNTIME_CREDS}/snapshot-passphrase"

export CREDENTIALS_DIRECTORY="${RUNTIME_CREDS}"
python3 "${SCRIPT_DIR}/scheduled-snapshot.py"
