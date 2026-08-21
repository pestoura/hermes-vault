#!/usr/bin/env bash
# READ-ONLY checklist printer for Hermes Vault bootstrap. No live operation.
set -euo pipefail
cat <<'CHECKLIST'
================================================================
 Hermes Vault — BOOTSTRAP CHECKLIST (READ-ONLY / ADR-022)
================================================================
 [0] PRECONDITIONS
  [ ] pinned Vault 1.21.4 running with strict TLS
  [ ] operator shell has VAULT_ADDR / VAULT_CACERT
  [ ] recovery material remains out-of-band

 [1] INIT — operator-only HITL
  [ ] initialize Shamir 3/2
  [ ] distribute 3 shares independently and preserve initial root out-of-band

 [2] UNSEAL — operator-only HITL
  [ ] present two distinct shares
  [ ] verify initialized=true and sealed=false

 [3] ENABLE AUDIT — operator-only HITL, MUST PRECEDE JIT
  [ ] enable canonical file/ audit device
  [ ] verify audit device is active before further bootstrap

 [4] JIT CERT ADMIN BOOTSTRAP — operator-only HITL
  [ ] prepare a dedicated self-signed ClientAuth leaf certificate
  [ ] keep its secret key out of Git/Hermes/Context Core/prompts
  [ ] apply ADR-022 issuer policies, cert auth role and hermes-vault-admin token role

 [5] INDEPENDENT JIT PROOF — operator-only HITL
  [ ] authenticate with the certificate without root
  [ ] mint a <=10m non-renewable orphan JIT token
  [ ] verify required capability and an explicit negative capability
  [ ] revoke/expire the JIT token

 [6] REVOKE INITIAL ROOT — operator-only HITL
  [ ] only after independent JIT proof is PASS
  [ ] confirm the initial root token is no longer usable

 REMINDER: this printer performs NO secret operation.
================================================================
CHECKLIST
echo "[checklist] printed ADR-022 bootstrap checklist only."
