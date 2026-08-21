#!/usr/bin/env bash
# Runtime loader for user-scoped encrypted snapshot credentials.
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
: "${RUNTIME_DIRECTORY:?systemd RuntimeDirectory is required}"
: "${VAULT_BACKUP_SECRET_BLOB:?encrypted backup SecretID path is required}"
: "${VAULT_SNAPSHOT_PASSPHRASE_BLOB:?encrypted snapshot passphrase path is required}"

[[ -d "${RUNTIME_DIRECTORY}" ]] || {
  echo "SCHEDULED_SNAPSHOT_FAIL reason=runtime_dir_missing" >&2
  exit 3
}
[[ -r "${VAULT_BACKUP_SECRET_BLOB}" && -r "${VAULT_SNAPSHOT_PASSPHRASE_BLOB}" ]] || {
  echo "SCHEDULED_SNAPSHOT_FAIL reason=encrypted_credentials_missing" >&2
  exit 3
}

RUNTIME_CREDS="${RUNTIME_DIRECTORY}/credentials"
mkdir -m 700 "${RUNTIME_CREDS}"
cleanup() {
  rm -rf -- "${RUNTIME_CREDS}"
}
trap cleanup EXIT
systemd-creds --user --name=backup-secret-id decrypt \
  "${VAULT_BACKUP_SECRET_BLOB}" "${RUNTIME_CREDS}/backup-secret-id" >/dev/null
systemd-creds --user --name=snapshot-passphrase decrypt \
  "${VAULT_SNAPSHOT_PASSPHRASE_BLOB}" "${RUNTIME_CREDS}/snapshot-passphrase" >/dev/null
chmod 600 "${RUNTIME_CREDS}/backup-secret-id" "${RUNTIME_CREDS}/snapshot-passphrase"

export CREDENTIALS_DIRECTORY="${RUNTIME_CREDS}"
python3 "${SCRIPT_DIR}/scheduled-snapshot.py"
