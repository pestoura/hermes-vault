# ADR-022 — Audit-first certificate JIT admin bootstrap

**Status:** repository procedure ready; live audit/JIT bootstrap/root revoke remain `NOT_RUN` until operator HITL execution. Init/unseal and Vault health are verified separately.

This procedure never records a Shamir share, token value, certificate secret key, passphrase, or recovery locator. Run it directly on HermesJarvas from the canonical repository. Disable shell tracing (`set +x`) before any token-bearing step.

## Security contract

- Audit is active before any post-bootstrap administration is installed.
- The operator certificate is a dedicated self-signed leaf, `CA:FALSE`, with `ClientAuth` Extended Key Usage (EKU).
- Certificate login receives only `vault-admin-issuer`.
- `vault-admin-issuer` may mint only against token role `hermes-vault-admin`.
- JIT tokens are orphaned, non-renewable, have no default policy, and have a hard maximum lifetime of 10 minutes.
- Root is revoked only after a non-root positive + negative capability proof passes.

### 1. Prepare operator-controlled certificate paths

Choose paths under operator-controlled custody **outside the repository**. These are placeholders, not canonical custody locations:

```bash
set +x
VAULT_ADMIN_KEY_PEM="<operator-controlled>/vault-admin-issuer.key"
VAULT_ADMIN_CERT_PEM="<operator-controlled>/vault-admin-issuer.pem"
export VAULT_ADMIN_KEY_PEM VAULT_ADMIN_CERT_PEM
```

### 2. Generate the encrypted dedicated ClientAuth leaf (HITL)

Keep the secret key encrypted at rest; OpenSSL must prompt for its passphrase.

```bash
umask 077
openssl req -x509 -newkey rsa:3072 -sha256 -days 365 \
  -keyout "${VAULT_ADMIN_KEY_PEM}" \
  -out "${VAULT_ADMIN_CERT_PEM}" \
  -subj "/CN=hermes-vault-admin-operator" \
  -addext "basicConstraints=critical,CA:FALSE" \
  -addext "keyUsage=critical,digitalSignature,keyEncipherment" \
  -addext "extendedKeyUsage=clientAuth"
```

Validate public metadata only:

```bash
openssl x509 -in "${VAULT_ADMIN_CERT_PEM}" -noout \
  -subject -issuer -dates -ext basicConstraints -ext extendedKeyUsage
```

### 3. Enable audit with bootstrap root

Load the initial root token interactively; never put it in shell history or command arguments:

```bash
read -rsp 'Initial root token: ' VAULT_TOKEN; echo
export VAULT_TOKEN
export VAULT_AUDIT_OPERATOR_ACK=yes
bash deployments/vault/scripts/enable-audit.sh
unset VAULT_AUDIT_OPERATOR_ACK
```

Verify safe audit metadata only:

```bash
docker compose -f deployments/vault/docker-compose.yml \
  --project-directory deployments/vault \
  exec -T -e VAULT_TOKEN vault vault audit list
```

Expected: `file/` exists. `AUDIT_PASS` is not declared until the live audit validation gate also passes.

### 4. Install the JIT admin chain

Still using bootstrap root only through the shell environment:

```bash
export VAULT_JIT_ADMIN_OPERATOR_ACK=yes
bash deployments/vault/scripts/bootstrap-jit-admin.sh
unset VAULT_JIT_ADMIN_OPERATOR_ACK
unset VAULT_TOKEN
```

Root is now absent from the active environment before certificate-path testing.

Define the pinned-container CLI wrapper:

```bash
vaultc() {
  docker compose -f deployments/vault/docker-compose.yml \
    --project-directory deployments/vault \
    exec -T -e VAULT_TOKEN vault vault "$@"
}
```

### 5. Prove JIT with root absent

Authenticate over the loopback TLS endpoint with the encrypted operator certificate. The issuer token exists only in shell memory:

```bash
ISSUER_TOKEN="$(
  curl --fail-with-body --silent --show-error \
    --cacert deployments/vault/certs/ca.pem \
    --cert "${VAULT_ADMIN_CERT_PEM}" \
    --key "${VAULT_ADMIN_KEY_PEM}" \
    --request POST \
    --header 'Content-Type: application/json' \
    --data '{"name":"vault-admin-issuer"}' \
    https://127.0.0.1:8200/v1/auth/cert/login \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["auth"]["client_token"])'
)"
export VAULT_TOKEN="${ISSUER_TOKEN}"
```

Mint one JIT token with only the policy-administration class:

```bash
JIT_TOKEN="$(vaultc token create -field=token \
  -role=hermes-vault-admin \
  -policy=vault-admin-policy \
  -ttl=10m \
  -renewable=false \
  -no-default-policy)"
unset ISSUER_TOKEN
export VAULT_TOKEN="${JIT_TOKEN}"
```

Positive capability must allow policy administration. Negative capability must be `deny` for audit administration because `vault-admin-audit` was not requested:

```bash
vaultc token capabilities sys/policies/acl/adr022-proof
vaultc token capabilities sys/audit/file
```

Expected: first result includes `create`/`update`; second result is `deny`. Inspect safe token metadata and confirm orphan, non-renewable, TTL `<=600s`, and only `vault-admin-policy`:

```bash
vaultc token lookup
```

Self-revoke the JIT token and clear ephemeral variables:

```bash
vaultc token revoke -self
unset JIT_TOKEN
unset VAULT_TOKEN
```

If any positive, negative, TTL, orphan, policy or revoke condition fails: **stop; do not revoke root**.

### 6. Revoke initial root

Reload initial root interactively from out-of-band custody and revoke the currently authenticated token itself:

```bash
read -rsp 'Initial root token for final revoke: ' VAULT_TOKEN; echo
export VAULT_TOKEN
vaultc token revoke -self
```

The same revoked token must fail self-lookup:

```bash
if vaultc token lookup >/dev/null 2>&1; then
  echo 'ROOT_REVOKE_VERIFY_FAILED' >&2
  exit 1
else
  echo 'ROOT_REVOKED'
fi
unset VAULT_TOKEN
```

Only this successful sequence permits the evidence label `ROOT_REVOKED`.

### 7. Post-revoke smoke

Repeat certificate login and one short JIT issuance after root revocation. Confirm the intended capability, confirm an out-of-scope capability is denied, self-revoke the JIT token and clear variables.

A failure after root retirement is a recovery event. Do not create or persist a permanent root token as an operational workaround.
