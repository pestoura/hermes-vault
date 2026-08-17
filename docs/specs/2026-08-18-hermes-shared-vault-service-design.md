# Hermes Shared Vault Service — Design Spec

- **Status:** Design / specification only. Not implemented. No runtime, deployment, policy, workflow, or secret material is created or mutated by this document.
- **Date:** 2026-08-18
- **Base SHA (exact current `main`):** `fec7b5b0a63165a93f5b6e919959094cfced569a`
- **Owner of service:** `pestoura/hermes-vault`
- **First consumer:** `pestoura/hermes-security-labs` (HSL)
- **Scope of this change:** documentation only, on an isolated branch from exact `main`. No code, no compose, no policies, no workflows, no HSL modification, no GitHub PR/issue mutation.

## 1. Purpose

Define the canonical design for HashiCorp Vault as a **shared security service for HermesJarvas**, owned and operated by `pestoura/hermes-vault`, consumed by HermesJarvas sub-projects (starting with HSL) through a provider-neutral capability contract. The service is the Secrets, Identity & Trust Plane described in the existing blueprint (`README.md`, `docs/00`–`docs/15`), but explicitly **not dedicated to Hermes Security Labs**.

This spec resolves the approved architecture decision: Vault is a shared service, not a lab-embedded deployment.

## 2. Non-goals

- This document is not an implementation plan, runbook, or migration execution plan.
- It does not define concrete policy files, compose files, Ansible/systemd units, or CI workflows (those are implementation concerns).
- It does not open or close GitHub PRs/issues.
- It does not perform any Vault operation: no init, unseal, root, SecretID, token, or recovery action.
- It does not assume HashiCorp Vault Enterprise or HCP features.
- It does not decide the custody location of recovery material (that is an owner responsibility, kept out of the repository per `SECURITY.md`).

## 3. Ownership boundary

| Concern | Owns | Does NOT own |
|---|---|---|
| Vault deployment, lifecycle, upgrade, storage, TLS termination, seal/unseal procedure | `hermes-vault` | HSL or any consumer |
| Recovery material custody and break-glass runbook | `hermes-vault` (custody out-of-band, outside Hermes/GitHub) | consumers |
| Audit device configuration and retention | `hermes-vault` | consumers |
| Capability contract definition and versioning | `hermes-vault` | consumers |
| Per-consumer mount creation, AppRole issuance, exact-path policies | `hermes-vault` (on request, with contract) | consumers |
| Consumer-internal use of issued capabilities | consumer (e.g. HSL) | `hermes-vault` |
| Consumer application logic, evidence semantics, tool behavior | consumer | `hermes-vault` |
| Secret values stored in KV/Transit for a consumer | jointly: consumer supplies/owns the secret value; `hermes-vault` stores and protects it under the consumer's dedicated mount | — |

**Principle:** consumers depend on the capability contract, not on Vault internals or on owning a Vault deployment. A consumer may be decommissioned or migrated without `hermes-vault` changing its deployment model.

## 4. Edition: Vault Community / OSS

MVP uses **HashiCorp Vault Community/OSS** only. No Enterprise/HCP feature is required or assumed (ADR-013). Specifically:

- No Enterprise **namespaces**; isolation is achieved through dedicated mounts and exact-path policies.
- No Enterprise replication, PKI automation, or HCP auto-unseal.
- If a future requirement provably needs an Enterprise/HCP feature, that becomes a new ADR with owner approval (per `docs/14` version rule), not a silent dependency.

## 5. Deployment model: Docker (supersedes earlier systemd host topology)

MVP deploys Vault as a **Docker container** on the Jarvas host.

This **supersedes** the earlier `docs/01-reference-architecture.md` "Plano físico inicial recomendado", which recommended native `vault.service` / `vault-agent.service` / `credential-broker.service` systemd units on the host. The intent of that section — a single Vault node on the Jarvas host, storage under a dedicated path — is preserved; the **mechanism** (systemd host units) is replaced by Docker for portability, isolation, and reproducible deployment. `docs/01` is retained as historical context; this spec is the current decision.

Deployment constraints (design-level, to be enforced at implementation):

- Official `hashicorp/vault` image, pinned by digest.
- Container runs with `read_only` root filesystem, `cap_drop: ALL`, `no-new-privileges`.
- Vault data persisted on a dedicated Docker volume with restricted ownership; not on a shared or world-readable path.
- Network exposure limited to what consumers require (design assumes loopback/container-network TLS on the Jarvas host; exact bind/port is an owner decision — see §19).
- Healthcheck and controlled restart procedure owned by `hermes-vault`.

## 6. Storage: single-node Integrated Storage / Raft

- MVP uses **Vault Integrated Storage (Raft)**, single node (ADR-006).
- No Consul. No multi-node HA in MVP.
- Single-node is an accepted MVP tradeoff (see §16); HA is a Later/Future item, not a blocker for first usable baseline.

## 7. TLS mandatory

- Vault listens only with **TLS enabled**; plain HTTP listener is not used for the operational API.
- Certificates are issued and managed per the PKI design (`docs/06`); until PKI is operational, a locally provisioned TLS cert is used, but TLS itself is non-optional.
- mTLS between internal components is a Later item (`docs/06`); the MVP requires at minimum server TLS on the Vault API.

## 8. Seal: manual Shamir 3/2, no auto-unseal in MVP

- MVP uses **Shamir manual unseal with threshold 2 of 3 key shares**.
- **No auto-unseal** in MVP. Rationale: the Jarvas environment is personal/self-hosted; introducing an external auto-unseal dependency would reduce recoverability (per `docs/09` seal-design guidance).
- Recovery/unseal material is handled out-of-band, outside Hermes, outside GitHub, outside the Vault storage it unlocks (ADR-002, `docs/09`).
- After restart, Vault remains sealed until an operator with the required quorum performs manual unseal using the out-of-band procedure.
- This spec performs **no** unseal, root, or Shamir operation.

## 9. Audit mandatory

- At least one **audit device** is enabled and functional before any consumer secret of value is migrated (ADR-011).
- Audit logs are treated as sensitive security data: no tokens, SecretIDs, private keys, recovery keys, or secret contents are sent to observability in clear (per `docs/08` redaction rules).
- Audit device availability is a production-readiness gate; absence blocks promotion to production use.

## 10. Backup and recovery: snapshots + isolated restore drill before real use

- Integrated Storage snapshots on a defined schedule, with an independent encrypted copy and checksum/metadata (ADR-012, `docs/09`).
- **A restore drill in an isolated, non-production environment is mandatory before the service is declared production-ready or before any real consumer secret is migrated.**
- Restore-drill acceptance (minimum): start isolated Vault; restore snapshot; validate storage/metadata; authenticate with a test identity; read a synthetic acceptance secret; assert cross-path policy deny; validate Transit metadata where applicable; tear down the test environment.
- A backup without a passing restore drill is not considered validated recovery (ADR-012).

## 11. Per-consumer isolation

Each consumer (e.g. HSL, future GitHub tool, Grafana tool, etc.) is isolated by:

1. **Dedicated mounts.** Separate secrets/transit mounts per consumer (e.g. `kv-hsl/`, `hsl-transit/`), not a shared `secret/` tree with path prefixes alone. This provides isolation without Enterprise namespaces.
2. **Dedicated AppRole.** One AppRole per consumer identity, with RoleID + wrapped single-use SecretID, bounded TTL, CIDR limits when stable.
3. **Exact-path policies.** Policies grant only the precise paths the consumer needs (e.g. `transit/sign/hsl-transit/hsl-signing`, `transit/verify/hsl-transit/hsl-signing`, `transit/keys/hsl-transit/hsl-signing` read-metadata). No `path "*"` for normal operation.
4. **Negative-capability tests.** For every consumer AppRole, automated tests assert denial of:
   - any path outside its dedicated mount(s);
   - `sys/*`, `auth/*`, `identity/*` administrative paths;
   - `transit/sign`/`transit/verify` for other consumers' keys;
   - list/delete/read on other consumers' mounts;
   - any capability broader than the contract.

Isolation failures block consumer activation.

## 12. No Enterprise namespaces assumption

All multi-tenant isolation is expressed through **separate mounts + exact-path policies + separate AppRoles**. The design never relies on Enterprise namespaces. If namespace-like behavior is later desired, it must be re-approved as an Enterprise ADR, not assumed.

## 13. HSL as first consumer: dedicated transit mount/key

HSL consumes the shared service through the capability contract with:

- A **dedicated Transit mount** (e.g. `hsl-transit/`).
- A **dedicated signing key** under that mount (e.g. `hsl-signing`), used for HSL evidence/execution signing.
- A **dedicated AppRole** (`hsl-signer`) whose policy allows only the HSL transit operations above and nothing else.
- No access to other consumers' mounts, to `sys/*`, or to administrative paths.

HSL's existing in-repo deployment (`deployment/vault-lab-l1/`) is **not** the owner of the shared service under this design (see §15). HSL becomes a consumer only.

## 14. Provider-neutral capability contract (no secret material)

The integration boundary between consumers (including HSL) and the Vault service is a **provider-neutral capability contract**. The contract:

- Describes **capabilities**, not secrets: `capability_type` (delegated_operation | ephemeral_token | wrapped_secret | certificate | dynamic_credential), `principal`, `action`, `resource_scope`, `risk_class`, `requested_ttl`, and correlation identifiers (`execution_id`, `plan_id`, `request_id`).
- Carries **no secret material**: no token string, SecretID, private key, or raw secret value is present in the contract layer.
- Is **provider-neutral**: it abstracts the secret backend so a consumer depends on the contract, not on Vault-specific APIs. The backing implementation (Vault Community/OSS in MVP) is replaceable without changing consumer code, provided the contract is honored.
- Resolves intent to the minimum necessary capability and delivers it via the safest available mode (delegated operation preferred; response wrapping/memory-only before tmpfs; static secret last), per `docs/04`.

This contract is the successor design to the generic `secret.read` anti-pattern (ADR-005). The concrete `VaultCredentialProvider` implementation lives in the bridge/provider layer and is an implementation concern, not part of this spec.

## 15. Secret-zero constraints

The first credential each workload uses to authenticate to Vault (AppRole SecretID, certificate, or JWT) is a **secret-zero** problem requiring explicit design (ADR-017). Constraints:

- Secret-zero material is never placed in a consumer's `.env`, in the Hermes state DB, in GitHub, or in logs.
- SecretID is delivered wrapped, single-use, short TTL; CIDR-bound when stable.
- Bootstrap of a consumer identity is performed by `hermes-vault` through a controlled, audited procedure; it is not "moving the secret to another file."
- This spec performs **no** SecretID issuance, wrapping, or token operation.

## 16. Lifecycle states and fail-closed behavior

### 16.1 Service lifecycle states

| State | Meaning | Entry condition |
|---|---|---|
| `UNINITIALIZED` | Vault installed, not initialized | fresh deployment |
| `INITIALIZED_SEALED` | Initialized, sealed, not serving | after init or restart |
| `UNSEALED_READY` | Unsealed, audit enabled, mounts/policies active | after quorum unseal + bootstrap |
| ERROR | degraded, must not serve real secrets | audit down, policy drift, storage fault |
| `DECOMMISSIONED` | retired, data handled per retention | owner decision |

### 16.2 Consumer contract lifecycle

| State | Meaning |
|---|---|
| `CONTRACT_DRAFT` | proposed capability contract |
| `CONTRACT_REVIEWED` | reviewed against isolation + negative-test criteria |
| `CONTRACT_ACTIVE` | consumer may use the capability |
| `CONTRACT_DEPRECATED` | scheduled for retirement, new issuances stopped |
| `CONTRACT_RETIRED` | removed, mounts/AppRole revoked |

### 16.3 Fail-closed rules

- If Vault is `SEALED` / unavailable / `ERROR`, consumers **fail closed**: no automatic fallback to static, more permissive local credentials (ADR-015).
- If a policy, contract validation, or identity check fails, the capability is denied.
- If the restore drill has not passed, the service must not be declared production-ready (ADR-012).
- If audit device is unavailable, promotion/real-secret use is blocked.
- A red security/contract/recovery regression in `hermes-vault` blocks related consumer activation until resolved (consistent with `docs/15` delivery model).

## 17. Migration from current HSL-owned deployment

Current state: HSL owns a Vault deployment under `deployment/vault-lab-l1/` (single-node Raft, TLS, AppRole signer, transit key `hermes-lab-l1-signer`).

Target state: `hermes-vault` owns the shared service; HSL consumes via contract with a dedicated transit mount/key.

Migration principles (design-level; execution is implementation):

1. Stand up the shared service per this spec (Docker, Raft, TLS, Shamir 3/2, audit, restore drill) before HSL depends on it.
2. Create HSL's dedicated mount/key/AppRole under the shared service; verify with negative-capability tests.
3. Repoint HSL's signing/evidence path from `deployment/vault-lab-l1` transit to the shared `hsl-transit/hsl-signing` (or retained verify-only mount during transition — see §19).
4. Decommission or freeze the HSL-owned deployment only after the shared path is validated and the key-continuity decision (§19) is made.
5. HSL is not modified by this spec; the migration execution is a separate implementation effort.

## 18. PR #17 superseded handling and PR-chain implications

- PR #17 (`epic-03/credential-broker-core`) is marked **SUPERSEDED ARCHITECTURE — DO NOT MERGE**. Its handling, and the implications for the stacked PR chain (#14 → #15 → #16 → #17/#18), are **implementation concerns** and are explicitly **out of scope for this specification**.
- This spec does not merge, close, reopen, or modify any PR or issue. It records only that the shared-service ownership boundary supersedes the lab-dedicated deployment assumption that earlier PRs may have presupposed.
- The PR-chain reconciliation (whether #17 is closed, rewritten, or absorbed; how #18's `VaultCredentialProvider` aligns with the provider-neutral contract) is deferred to implementation planning.

## 19. MVP / Later / Future split

**MVP (this service's first usable baseline):**
- Docker single-node Vault Community/OSS.
- Integrated Storage / Raft.
- TLS mandatory.
- Manual Shamir 3/2, no auto-unseal.
- Audit device mandatory.
- Snapshots + isolated restore drill before real use.
- First consumer (HSL) with dedicated transit mount/key + AppRole + exact-path policy + negative-capability tests.
- Provider-neutral capability contract defined (no secret material).

**Later:**
- PKI/mTLS between internal components (`docs/06`).
- Additional consumers (GitHub, Grafana, etc.) with dedicated mounts.
- Certificate/JWT auth replacing or complementing AppRole where stronger identity exists (`docs/03`).
- JIT L3 admin (`hermes-vault-admin`) with short TTL, approval, revocation, evidence (`docs/05`, ADR-003).
- Dynamic secrets where providers support them (ADR-008).
- Secret migration breadth from existing `.env`/static stores (`docs/11`).

**Future:**
- Multi-node Raft / HA if operational need justifies it.
- Formal Enterprise/HCP evaluation only via new ADR if a concrete requirement appears (ADR-013).
- Cross-host Vault isolation / dedicated host or VM.

## 20. Risks and accepted tradeoffs

| Risk / tradeoff | Decision | Mitigation |
|---|---|---|
| Single node: no HA, downtime on restart until manual unseal | Accepted for MVP (ADR-006, ADR-013) | Monitoring, documented unseal runbook, restore drill |
| Manual Shamir 3/2: operator must unseal after restart; no auto-recovery | Accepted; avoids external auto-unseal dependency (`docs/09`) | Quorum procedure, out-of-band custody, drill |
| Docker adds container-runtime dependency vs native systemd | Accepted for isolation/portability (supersedes `docs/01` systemd plan) | `read_only`, `cap_drop ALL`, `no-new-privileges`, dedicated volume |
| No Enterprise namespaces: more mount management | Accepted (ADR-013) | Dedicated mounts + exact-path policies + negative tests |
| Shared service increases blast radius if Vault compromised | Mitigated by per-consumer isolation, audit, negative tests | Fail-closed, contract review gate |
| Key continuity for existing HSL-signed evidence (non-exportable key) | **Owner decision required** (§21) | Verify-only retained mount or re-sign policy |
| Recovery material custody | Out-of-band, owner responsibility, never in repo (`SECURITY.md`) | Documented quorum + offline runbook |

## 21. Testing and verification strategy

### 21.1 This specification (design change) is verified by

- No placeholder/TODO/TBD/FIXME text remains in the document.
- No contradiction between sections (edition, deployment, seal, ownership, isolation).
- No secret material, no real token/SecretID/recovery value present.
- Consistent with existing ADRs (`docs/13`); superseded assumptions recorded, historical docs not deleted.
- Single isolated commit on a branch from exact `main` `fec7b5b0a63165a93f5b6e919959094cfced569a`; only the spec file added.

### 21.2 Future implementation verification (design-level checklist)

- Static policy lint (no wildcard/sudo for normal identities).
- Negative-capability matrix tests per consumer AppRole.
- Restore-drill acceptance in isolated environment.
- Audit device functional test (auth + capability events present, redaction verified).
- TLS strictness test (no plain-HTTP operational listener).
- Shamir quorum test in non-production (threshold behavior).
- Provider-neutral contract conformance tests (consumer depends on contract, not Vault API).
- HSL dedicated mount isolation tests (sign/verify own key; denied cross-path).
- Fail-closed test (sealed Vault → consumer denied, no fallback).

## 22. Invariants for THIS change

The following hold for the design/spec change only and are not violated by it:

- No Vault runtime is installed, started, initialized, unsealed, or modified.
- No root token, recovery key, Shamir share, SecretID, or token is created, read, printed, or transmitted.
- No real secret material is referenced or stored in the repository.
- No deployment files, policies, compose files, or workflows are written (only this design document).
- `pestoura/hermes-security-labs` and any other repository are not modified.
- No GitHub PR or issue is opened, closed, or mutated.
- The change is documentation-only on an isolated branch from exact `main`.

## 23. Reconciliation with existing docs / ADRs

This spec **preserves** all historical ADRs in `docs/13` (ADR-001 through ADR-017). It does not delete or rewrite them. It records the following **superseded earlier assumptions**:

1. **Systemd host topology superseded.** `docs/01-reference-architecture.md` "Plano físico inicial recomendado" recommended native `vault.service`/`vault-agent.service` systemd units. This spec adopts **Docker** as the MVP deployment mechanism. The single-node-on-Jarvas-host intent is preserved; the mechanism is changed. `docs/01` remains as historical context.
2. **Lab-dedicated ownership superseded.** The earlier model (and HSL's `deployment/vault-lab-l1/`) treated Vault as a lab-embedded deployment owned by HSL. This spec establishes Vault as a **shared security service owned by `hermes-vault`**, with HSL as first consumer. HSL ownership of a Vault deployment is superseded for the target architecture.
3. **No conflict with ADR-006/013.** Single-node Raft and Community-first remain the baseline; this spec reinforces them.
4. **No conflict with ADR-002/011/012/015/017.** Root-out-of-Hermes, audit-before-migration, restore-drill gate, fail-closed, and explicit secret-zero design are all reinforced.

## 24. Self-review result

- Placeholders/TODO/TBD/FIXME: none present.
- Contradictions: none found. Edition (Community/OSS), deployment (Docker), seal (manual Shamir 3/2, no auto-unseal), ownership (shared service), and isolation (dedicated mounts, no namespaces) are internally consistent.
- Ambiguity: resolved where possible; genuinely structural open items are listed in §25 rather than left implicit.
- Secret hygiene: no secret values, tokens, SecretIDs, or recovery material present.
- ADR alignment: consistent; superseded assumptions explicitly recorded without deleting history.

## 25. Unresolved structural decisions requiring owner input

These are genuine structural choices that this spec deliberately does not decide; they require owner decision before or during implementation:

1. **Key continuity for existing HSL-signed evidence.** The current HSL transit key `hermes-lab-l1-signer` is non-exportable (`exportable=false`, `allow_plaintext_backup=false`). It cannot be migrated as material to the shared `hsl-transit` mount. Owner must decide: (a) retain the old HSL mount read-only for `verify` during a transition window; (b) accept that historical signatures become unverifiable and re-sign evidence with the new key; or (c) define a verify-continuity policy. This affects migration safety, not the shared-service design.
2. **Network exposure model.** Design assumes Vault is reached by consumers via loopback/container-network TLS on the Jarvas host. Owner must confirm exact bind address, port, and how HSL (a separate deployment/repo) connects to the shared service.
3. **HSL deployment cutover vs parallel-run.** Owner must decide whether `deployment/vault-lab-l1` is decommissioned after migration, kept read-only for verify, or run in parallel during transition.
4. **Recovery material custody.** Out-of-band custody location is an owner responsibility and must never enter the repository (`SECURITY.md`). The design requires it to be outside Hermes/GitHub/host-readable paths, but the concrete location is owner-decided.
5. **Exact image version and registry.** Design requires the official `hashicorp/vault` image pinned by digest. Owner confirms the specific version and whether an internal mirror is used.
