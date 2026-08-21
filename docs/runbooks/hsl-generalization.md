# HSL `vault-lab-l1` Generalization — Mapping & Ownership (Task I1)

Provenance:
  source_plan: docs/superpowers/plans/2026-08-18-hermes-shared-vault-service.md (Task I1, lines 912-927)
  reference_read_only: pestoura/hermes-security-labs `deployment/vault-lab-l1`
  worktree: hermes-shared-vault-service-implementation
  mode: repo-side / static ONLY (no Vault started, no HSL mutation, no secrets)

## Headline

`hermes-vault` owns the shared Vault service lifecycle. The working patterns
from HSL's `deployment/vault-lab-l1` are lifted INTO this shared service as the
canonical baseline under `deployments/vault/`. HSL does NOT re-own the result
(spec §15/§17). No replica `deployment/vault-lab-l1` is created in this repo —
`tests/isolation/test_ownership_boundary.py` asserts its absence.

HSL's `deployment/vault-lab-l1` is a **read-only reference** here. Its digest,
Raft/TLS/AppRole design, and signer transit key are the source of patterns; the
committed, provider-owned artifacts in `hermes-vault` are the canonical service.

## Pattern → shared-service artifact mapping

| HSL `vault-lab-l1` pattern (reference) | Canonical shared-service artifact (owned by hermes-vault) | Notes / contract |
|---|---|---|
| Image `hashicorp/vault:1.21.4@sha256:4e33b126a59c0c333b76fb4e894722462659a6bec7c48c9ee8cea56fccfd2569` | `deployments/vault/Dockerfile` + `docker-compose.yml` (Community/OSS only) | Same pinned digest; no Enterprise/HCP/auto-unseal. |
| Single-node Integrated Storage (Raft), `node_id=hermes-lab-l1-vault-1` | `deployments/vault/config/vault.hcl` (Raft storage) | Generalized node_id; provider-owned lifecycle. |
| Mandatory TLS (`tls_min_version=tls12`, CA client verification, no `VAULT_SKIP_VERIFY`) | `deployments/vault/scripts/provision-tls.sh` (operator-managed material, never committed) | Operator TLS custody; `VAULT_SKIP_VERIFY` forbidden. |
| Manual Shamir 3/2 init + unseal (HITL) | `deployments/vault/scripts/bootstrap-checklist.sh` + `docs/runbooks/vault-bootstrap.md` | Operator-only; never auto-executed. |
| `transit/keys/hermes-lab-l1-signer` (ed25519, sign/verify) | `hsl-transit/` mount + `hsl-signing` key (spec §13, E1) | Dedicated**consumer** mount; provider-owned enable script `enable-hsl-transit.sh`. |
| Signer AppRole exact paths (`transit/sign|verify|keys/hsl-transit/hsl-signing`, no wildcard/sudo) | `hsl-signer` AppRole + `policies/hsl/hsl-signer.hcl` (spec §11.2-§11.3, E2) | Exact-path policy; provider-owned enable script `enable-hsl-signer.sh`. |
| Signer SecretID delivery via response-wrapping, single-use, short TTL (HITL) | `docs/runbooks/secret-zero.md` (H1, INV-8/INV-10) | Live issuance stays operator HITL / NOT_RUN. |
| Operator-observer policy (`sys/health`, `sys/seal-status`, `auth/token/lookup-self`, mount read) | `deployments/vault/` operational scripts + audit policy | Read-only operator posture preserved. |
| Audit device required (redaction) | `deployments/vault/scripts/enable-audit.sh` + audit policy | One mandatory audit device; redaction enforced. |
| Restore drill / snapshot | `deployments/vault/scripts/restore-drill.sh`, `snapshot.sh` | Recovery/break-glass preserved. |

## Ownership boundary (must hold)

- `deployments/vault/` is the canonical, provider-owned service.
- `deployment/vault-lab-l1` (and any `deployment/vault-lab-l1`, `deployments/vault-lab-l1`) MUST NOT be created in this repo.
- HSL consumes via the published contract (`hsl-transit/hsl-signing`, `hsl-signer` AppRole). Cross-repo HSL repointing (Task M1) is specified, not performed here (INV-11).
- `hermes-vault` never writes to `pestoura/hermes-security-labs`; the reference is read-only.

## Contracts preserved by I1

- **E1 (spec §13):** `hsl-transit/` mount + `hsl-signing` key, provider-owned, HITL-gated, idempotent, data-free.
- **E2 (spec §11.2-§11.3):** `hsl-signer` AppRole exact-path policy, provider-owned, HITL-gated.
- **H1 (INV-8/INV-10):** secret-zero live SecretID issuance/wrapping stays operator HITL / NOT_RUN; runbook never claims live PASS unattended.

## NOT_RUN / out-of-scope (by design — never executed here)

- Live `vault operator init` / `unseal` / root handling.
- Live AppRole SecretID issuance/wrapping, TLS private-key generation/custody.
- Production promotion sign-off (restore drill + audit + owner sign-off required).
- Any HSL mutation: decommission/freeze of `deployment/vault-lab-l1` (I2), HSL consumer migration (K1), cross-repo handoff (M1). These are documented-only/owner-gated, never run inside `hermes-vault`.
