#!/usr/bin/env bash
#
# provision-tls.sh — Operator-only (HITL) local TLS provisioning for the
# Hermes Vault listener (Task B3, spec §7, ADR-019).
#
# Generates a self-signed CA and a server certificate into the git-ignored
# deployments/vault/certs/ directory. The private key material produced here is
# OPERATOR CUSTODY and is NEVER committed, printed, read back, or transmitted by
# automated tasks.
#
# The server certificate covers only the minimum MVP endpoints:
#   DNS:hermes-vault  — Docker-internal alias on hermes-security-plane
#   DNS:localhost     — local operator DNS access
#   IP:127.0.0.1      — local operator loopback access
#
# HITL ONLY: this script refuses to run unattended (no VAULT_TLS_OPERATOR_ACK)
# and never starts Vault or performs operator init/unseal — those remain operator
# steps (see B4). It MUST be executed by a human operator out-of-band, never by
# CI or unattended tasks. Recovery of TLS material is an operator responsibility.
#
# Pre-flight: the `openssl` CLI must be installed on the operator host.
set -euo pipefail

# HITL guard: refuse unattended execution.
if [[ "${VAULT_TLS_OPERATOR_ACK:-}" != "yes" ]]; then
  echo "HITL REFUSES: this script handles private TLS material and may only be" >&2
  echo "run by an operator out-of-band. Set VAULT_TLS_OPERATOR_ACK=yes to proceed." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Git-ignored output directory (deployments/vault/certs/).
OUTDIR="${VAULT_CERTS_DIR:-$SCRIPT_DIR/../certs}"

# Provisioned artifacts (git-ignored, operator-custodied):
#   certs/vault-server.key
#   certs/vault-server.pem
#   certs/ca.pem
CA_KEY="$OUTDIR/ca.key"
CA_CERT="$OUTDIR/ca.pem"
SERVER_KEY="$OUTDIR/vault-server.key"
SERVER_CSR="$OUTDIR/vault-server.csr"
SERVER_CERT="$OUTDIR/vault-server.pem"
EXTFILE="$OUTDIR/vault-server.ext"

DAYS="${VAULT_TLS_DAYS:-825}"
CN="${VAULT_TLS_CN:-hermes-vault}"

command -v openssl >/dev/null 2>&1 || { echo "openssl is required" >&2; exit 1; }

mkdir -p "$OUTDIR"
# CSR and extension config are transient. Remove them even if OpenSSL fails.
trap 'rm -f "$SERVER_CSR" "$EXTFILE"' EXIT

# 1) Self-signed CA.
openssl genrsa -out "$CA_KEY" 2048
openssl req -x509 -new -nodes -key "$CA_KEY" -sha256 -days "$DAYS" \
  -subj "/CN=hermes-vault-ca" -out "$CA_CERT"

# 2) Server key + CSR, signed by the CA with the minimum required SAN set.
openssl genrsa -out "$SERVER_KEY" 2048
openssl req -new -key "$SERVER_KEY" -subj "/CN=${CN}" -out "$SERVER_CSR"
cat >"$EXTFILE" <<'EOF'
subjectAltName=DNS:hermes-vault,DNS:localhost,IP:127.0.0.1
extendedKeyUsage=serverAuth
keyUsage=digitalSignature,keyEncipherment
EOF
openssl x509 -req -in "$SERVER_CSR" -CA "$CA_CERT" -CAkey "$CA_KEY" \
  -CAcreateserial -sha256 -days "$DAYS" -extfile "$EXTFILE" -out "$SERVER_CERT"
rm -f "$OUTDIR/ca.srl"

# Private key material is operator custody: restrict perms, never echo contents.
chmod 600 "$SERVER_KEY" "$CA_KEY"

echo "TLS material provisioned under ${OUTDIR} (git-ignored, operator custody)."
echo "Server certificate SAN contract: hermes-vault, localhost, 127.0.0.1."
echo "Do NOT commit these files. For production, provision certs via your PKI (Later)."
