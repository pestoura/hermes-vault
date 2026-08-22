# ADR-022 — Audit-first certificate JIT admin bootstrap

**Status:** `VERIFIED_ADR022_LIVE_ACCEPTED` on 2026-08-21. Audit, certificate JIT bootstrap, independent non-root JIT proof, initial-root self-revocation and post-revoke JIT smoke passed. This does **not** promote `UNSEALED_READY`: the restore drill is now `VERIFIED_ADR023_LIVE_ACCEPTED`, while first consumer bootstrap remains `NOT_RUN`. Administrative JIT self-revoke was revalidated live on 2026-08-22 for all six administrative classes; see `docs/evidence/2026-08-22-jit-self-revoke-revalidation.md`.

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

The issuer deliberately has no `sys/capabilities-self`. Prove least privilege by attempting a real administrative read and requiring Vault to deny it:

```bash
if ISSUER_DENY="$(vaultc policy read vault-admin-policy 2>&1)"; then
  echo 'ISSUER_NEGATIVE_FAILED' >&2
  exit 1
fi
grep -Eq 'Code: 403|permission denied' <<<"${ISSUER_DENY}" || {
  echo "${ISSUER_DENY}" >&2
  exit 1
}
unset ISSUER_DENY
echo 'ISSUER_NEGATIVE_PASS'
```

Mint one JIT token with only the policy-administration class. Validate its issuance metadata directly from the creation response so no `lookup-self` permission is required:

```bash
JIT_JSON="$(vaultc token create -format=json \
  -role=hermes-vault-admin \
  -policy=vault-admin-policy \
  -ttl=10m \
  -renewable=false \
  -no-default-policy)"

JIT_TOKEN="$(printf '%s' "${JIT_JSON}" | python3 -c '
import json,sys
x=json.load(sys.stdin)["auth"]
policies=x.get("token_policies") or x.get("policies") or []
assert policies == ["vault-admin-policy"], policies
assert 0 < int(x["lease_duration"]) <= 600
assert x["renewable"] is False
assert x["orphan"] is True
print(x["client_token"])
')"

unset JIT_JSON ISSUER_TOKEN
export VAULT_TOKEN="${JIT_TOKEN}"
echo 'JIT_METADATA_PASS'
```

Prove the requested class with a real permitted operation, and prove separation from the audit class with a real denied operation:

```bash
vaultc policy list >/dev/null
echo 'JIT_POSITIVE_PASS'

if AUDIT_DENY="$(vaultc audit list 2>&1)"; then
  echo 'JIT_NEGATIVE_FAILED' >&2
  exit 1
fi
grep -Eq 'Code: 403|permission denied' <<<"${AUDIT_DENY}" || {
  echo "${AUDIT_DENY}" >&2
  exit 1
}
unset AUDIT_DENY
echo 'JIT_NEGATIVE_PASS'
```

Every JIT class carries only the minimal self-retirement capability needed when the `default` policy is excluded. Self-revoke and prove the token can no longer perform its previously allowed operation:

```bash
vaultc token revoke -self

if vaultc policy list >/dev/null 2>&1; then
  echo 'JIT_REVOKE_VERIFY_FAILED' >&2
  exit 1
fi

unset JIT_TOKEN VAULT_TOKEN
echo 'ADR022_JIT_PROOF_PASS'
```

If any login, issuer-deny, issuance-metadata, positive, negative, or revoke condition fails: **stop; do not revoke root**.

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
