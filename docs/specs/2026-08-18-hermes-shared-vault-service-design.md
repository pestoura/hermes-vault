# Hermes Shared Vault Service — Design Spec

- **Status:** Approved design with `VAULT_CORE_OPERATIONAL=VERIFIED` on HermesJarvas (2026-08-22). Vault runtime remains `VERIFIED_UNSEALED_HEALTHY`; ADR-022 remains `VERIFIED_ADR022_LIVE_ACCEPTED`; Vault 1.21.4 is deployed with strict TLS, single-node Raft, Shamir 3/2, file audit, certificate JIT administration, initial-root retirement, `restart: unless-stopped`, secret-free readiness assurance and a daily encrypted Raft snapshot (`SCHEDULED_SNAPSHOT_PASS`). ADR-023 is `VERIFIED_ADR023_LIVE_ACCEPTED` with `RESTORE_DRILL_PASS`. `JIT_SELF_REVOKE_REVALIDATION=PENDING` records a narrow live policy/lifecycle revalidation after operator-side HTTP 403 cleanup observations. first-consumer acceptance remains `NOT_RUN`; `UNSEALED_READY` is therefore not yet claimed. No share, token, SecretID, passphrase or private-key material is recorded here.
- **Original design date:** 2026-08-18
- **Structural decision update:** 2026-08-21
- **Original design base SHA:** `fec7b5b0a63165a93f5b6e919959094cfced569a`
- **Owner of service:** `pestoura/hermes-vault`
- **First consumer:** `pestoura/hermes-security-labs` (HSL)
- **Scope:** canonical architecture and security contract for the shared Vault service. Repository-side implementation is maintained in `pestoura/hermes-vault`; this document itself performs no live Vault operation and carries no secret, recovery, token, SecretID, Shamir-share, or TLS private-key material.

## 1. Purpose

Define the canonical design for HashiCorp Vault as a **shared security service for HermesJarvas**, owned and operated by `pestoura/hermes-vault`, consumed by HermesJarvas sub-projects (starting with HSL) through a provider-neutral capability contract. The service is the Secrets, Identity & Trust Plane described in the existing blueprint (`README.md`, `docs/00`–`docs/15`), but explicitly **not dedicated to Hermes Security Labs**.

This spec resolves the approved architecture decision: Vault is a shared service, not a lab-embedded deployment.

## 2. Non-goals

- This document is not an implementation plan, runbook, or migration execution plan.
- It does not itself execute deployment, policy, workflow, or runtime changes; those are governed by implementation plans, tests, PRs and runbooks in this repository.
- It does not perform any Vault operation: no init, unseal, root, SecretID, token, or recovery action.
- It does not assume HashiCorp Vault Enterprise or HCP features.
- It never records the concrete custody location of recovery material; ADR-021 defines only the custody model and keeps locators out-of-band.

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

Deployment constraints:

- Official `hashicorp/vault` image, pinned by digest.
- Container runs with `read_only` root filesystem, `cap_drop: ALL`, `no-new-privileges`.
- Vault data persisted on a dedicated Docker volume with restricted ownership; not on a shared or world-readable path.
- Network exposure is resolved by ADR-019 and refined by ADR-019A: host publication remains exactly `127.0.0.1:8200:8200`; authorised container consumers use TLS only on the Docker-internal `hermes-security-plane` network through alias `hermes-vault`; a separate `hermes-vault-admin` bridge exists only to make that loopback administration path functional on Docker, carries no consumer alias, and has IP masquerade disabled. No LAN/Internet publication is part of the MVP.
- Healthcheck and controlled restart procedure owned by `hermes-vault`.

## 6. Storage: single-node Integrated Storage / Raft

- MVP uses **Vault Integrated Storage (Raft)**, single node (ADR-006).
- No Consul. No multi-node HA in MVP.
- Single-node is an accepted MVP tradeoff (see §16); HA is a Later/Future item, not a blocker for first usable baseline.

## 7. TLS mandatory

- Vault listens only with **TLS enabled**; plain HTTP listener is not used for the operational API.
- Certificates are issued and managed per the PKI design (`docs/06`); until PKI is operational, a locally provisioned TLS cert is used, but TLS itself is non-optional.
- The MVP server-certificate SAN contract covers `DNS:hermes-vault`, `DNS:localhost`, and `IP:127.0.0.1`; private-key generation/custody remains operator-only HITL.
- mTLS between internal components is a Later item (`docs/06`); the MVP requires at minimum server TLS on the Vault API.

## 8. Seal: manual Shamir 3/2, no auto-unseal in MVP

- MVP uses **Shamir manual unseal with threshold 2 of 3 key shares**.
- **No auto-unseal** in MVP. Rationale: the Jarvas environment is personal/self-hosted; introducing an external auto-unseal dependency would reduce recoverability (per `docs/09` seal-design guidance).
- Recovery/unseal material is handled out-of-band, outside Hermes, outside GitHub, outside the Vault storage it unlocks (ADR-002, ADR-021, `docs/09`).
- After restart, Vault remains sealed until an operator with the required quorum performs manual unseal using the out-of-band procedure.
- This spec performs **no** unseal, root, or Shamir operation.

## 9. Audit mandatory

- At least one **audit device** is enabled and functional before any consumer secret of value is migrated (ADR-011).
- Audit logs are treated as sensitive security data: no tokens, SecretIDs, private keys, recovery keys, or secret contents are sent to observability in clear (per `docs/08` redaction rules).
- Audit device availability is a production-readiness gate; absence blocks promotion to production use.

## 10. Backup and recovery: snapshots + isolated restore drill before real use

- Integrated Storage snapshots use strict loopback TLS capture, mandatory checksum metadata and an independently encrypted copy (ADR-012, ADR-023, `docs/09`).
- **A restore drill in an isolated, non-production environment is mandatory before the service is declared production-ready or before any real consumer secret is migrated.**
- ADR-023 fixes the MVP restore model: exact pinned Vault image, Docker `network=none`, zero published ports, no production Vault volumes/networks, run-scoped disposable Raft/audit storage and synthetic-only acceptance fixtures.
- Production JIT recovery may read a snapshot and manage only reserved synthetic fixtures; it never receives `snapshot-force`.
- `snapshot-force` is executed only by the operator inside the labelled disposable container after temporary initialization. After restore, the instance is unsealed with the original Shamir quorum (2/3) as HITL; automation enters no original Shamir share.
- Acceptance proves synthetic certificate login, primary KV read, explicit forbidden-path deny, Transit metadata read, token self-revoke, isolation and teardown. See `docs/runbooks/restore-drill.md`.
- Live recovery state is `VERIFIED_ADR023_LIVE_ACCEPTED`; `RESTORE_DRILL_PASS` is VERIFIED by `docs/evidence/2026-08-21-adr-023-live-acceptance.md`. first-consumer acceptance remains a separate `NOT_RUN` gate.
- A backup without a passing restore drill is not considered validated recovery (ADR-012).

## 11. Per-consumer isolation

Each consumer (e.g. HSL, future GitHub tool, Grafana tool, etc.) is isolated by:

1. **Dedicated mounts.** Separate secrets/transit mounts per consumer (e.g. `kv-hsl/`, `hsl-transit/`), not a shared `secret/` tree with path prefixes alone. This provides isolation without Enterprise namespaces.
2. **Dedicated AppRole.** One AppRole per consumer identity, with RoleID + wrapped single-use SecretID, bounded TTL, CIDR limits when stable.
3. **Exact-path policies.** Policies grant only the precise paths the consumer needs (e.g. `hsl-transit/sign/hsl-signing`, `hsl-transit/verify/hsl-signing`, `hsl-transit/keys/hsl-signing` read-metadata). No `path "*"` for normal operation.

> Reconciliation note: the `hsl-transit/` mount is the canonical dedicated HSL Transit mount; the HSL signer exact-path contract uses `hsl-transit/sign|verify|keys/hsl-signing` (no `transit/` prefix), matching the accepted E1 mount/key and E2 policy.
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

HSL's historical in-repo deployment (`deployment/vault-lab-l1/`) is **not** the owner of the shared service under this design (see §17). HSL becomes a consumer only.

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

### 15.1 Administrative secret-zero — ADR-022

Post-initialization administration uses an **audit-first certificate JIT** chain (ADR-022). Initial root is temporary bootstrap authority only: after audit is active, a dedicated self-signed ClientAuth leaf authenticates to `auth/cert` and receives only `vault-admin-issuer`. That issuer may create tokens solely against token role `hermes-vault-admin`; JIT tokens are orphaned, non-renewable, omit the default policy and have a hard 10-minute maximum TTL. Because omitting `default` also removes its self-management grants, every JIT class explicitly carries only `auth/token/revoke-self:update` as the common lifecycle capability required to retire itself.

The certificate secret key remains operator-only and outside Git, Hermes state, Context Core and prompts. Initial-root revocation is permitted only after an independent positive/negative capability proof succeeds with root absent from the active environment. This does not promote `UNSEALED_READY`: audit validation, JIT live acceptance, restore drill and consumer bootstrap remain separate live gates.

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

## 17. Migration from the historical HSL-owned deployment

Historical baseline: HSL was documented as owning a Vault deployment under `deployment/vault-lab-l1/` (single-node Raft, TLS, AppRole signer, transit key `hermes-lab-l1-signer`). That runtime state must be re-confirmed immediately before cross-repo execution; it is not inferred from this spec.

Target state: `hermes-vault` owns the shared service; HSL consumes via contract with a dedicated transit mount/key.

Migration principles (design-level; execution is implementation):

1. Stand up the shared service per this spec (Docker, Raft, TLS, Shamir 3/2, audit, restore drill) before HSL depends on it.
2. Create HSL's dedicated mount/key/AppRole under the shared service; verify with negative-capability tests.
3. After shared-service acceptance, repoint HSL signing/evidence to `hsl-transit/hsl-signing`; preserve the legacy `hermes-lab-l1-signer` path only for historical **verify-only** continuity as defined by ADR-018 and ADR-020.
4. Enter `SHARED_SIGN_ACTIVE_LEGACY_VERIFY_ONLY` only after the cutover gates in `docs/runbooks/hsl-key-continuity.md` pass. Retire the legacy verifier only after continuity/retention sign-off; do not bulk re-sign historical evidence.
5. HSL is not modified by this spec; the migration execution is a separate cross-repo implementation effort.

## 18. PR #17 superseded handling and PR-chain implications

- PR #17 (`epic-03/credential-broker-core`) is classified **SUPERSEDED ARCHITECTURE — DO NOT MERGE** by the implementation governance model; its historical design is not authoritative for the shared-service ownership boundary.
- The implementation process subsequently closes superseded PRs only with auditable rationale; the spec itself does not perform GitHub mutations.
- PR #18's `VaultCredentialProvider` remains a separate/deferred provider implementation aligned to the provider-neutral contract, not a generic `secret.read` surface.

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
| Key continuity for existing HSL-signed evidence (non-exportable key) | Resolved by ADR-018: legacy verify-only continuity | Preserve original signatures; no new legacy signing after cutover |
| Recovery material custody | Resolved by ADR-021: independent out-of-band Shamir 3/2 custody | No concrete custody locators in repo/Hermes/Jarvas |

## 21. Testing and verification strategy

### 21.1 Original specification change verification (historical)

The original design/spec change was documentation-only and was verified against its original base SHA. Those checks are retained as provenance; they are **not current implementation acceptance** and must not be used to infer runtime readiness.

Historical checks included:

- no placeholder/TODO/TBD/FIXME text in the design;
- no secret material or real token/SecretID/recovery value;
- consistency with ADR-001 through ADR-017 at the time;
- isolated documentation-only change from original design base `fec7b5b0a63165a93f5b6e919959094cfced569a`.

### 21.2 Current implementation acceptance and future live verification

Current implementation acceptance is evidence-driven through the implementation plan, exact-SHA PR review and repository gates. Safe repository-side checks include:

- full `pytest tests/ -m 'not hitl'` suite;
- policy lint and provider-neutral contract tests;
- lifecycle/global invariants and secret-zero tests;
- tracked-tree secret scan;
- `docker compose config` without create/start;
- static network/TLS/runbook contract tests.

Live gates remain separate and may only be claimed after execution:

- Vault health/unseal acceptance;
- negative-capability matrix against live consumer AppRole;
- isolated restore-drill acceptance;
- audit device functional test with redaction validation;
- TLS connectivity from authorised consumer path;
- Shamir quorum test in the approved non-production/HITL procedure;
- HSL sign/verify and historical legacy verify-continuity tests;
- fail-closed test with sealed/unavailable Vault.

## 22. Original design/spec change invariants (historical)

The following held for the **original design/spec change** only. They are preserved as provenance and are not claims about the current repository-side implementation. **Current implementation acceptance** is governed by §21.2 and the active implementation plan. Live Vault deployment/start, initialization and Shamir quorum unseal were separately executed and verified on HermesJarvas on 2026-08-21. `VAULT_HEALTH_PASS` and `VAULT_UNSEALED` are verified from strict-TLS HTTP 200 plus `initialized=true` / `sealed=false`. ADR-022 audit/JIT/root-retirement acceptance is separately evidenced as `VERIFIED_ADR022_LIVE_ACCEPTED`. ADR-023 live recovery is `VERIFIED_ADR023_LIVE_ACCEPTED` with `RESTORE_DRILL_PASS` VERIFIED by the live evidence. Consumer bootstrap and production promotion remain separate `NOT_RUN` gates until separately executed and evidenced.

- No Vault runtime was installed, started, initialized, unsealed, or modified by the original spec change.
- No root token, recovery key, Shamir share, SecretID, or token was created, read, printed, or transmitted.
- No real secret material was referenced or stored in the repository.
- No deployment files, policies, compose files, or workflows were written by the original documentation-only change.
- `pestoura/hermes-security-labs` and any other consumer repository were not modified.
- The original spec change itself performed no GitHub PR/issue mutation.

## 23. Reconciliation with existing docs / ADRs

This spec **preserves** all historical ADRs in `docs/13` (ADR-001 through ADR-017) and adds the approved ADR-018 through ADR-021 resolutions without deleting historical rationale. It records the following **superseded earlier assumptions**:

1. **Systemd host topology superseded.** `docs/01-reference-architecture.md` "Plano físico inicial recomendado" recommended native `vault.service`/`vault-agent.service` systemd units. This spec adopts **Docker** as the MVP deployment mechanism. The single-node-on-Jarvas-host intent is preserved; the mechanism is changed. `docs/01` remains as historical context.
2. **Lab-dedicated ownership superseded.** The earlier model (and HSL's historical `deployment/vault-lab-l1/`) treated Vault as a lab-embedded deployment owned by HSL. This spec establishes Vault as a **shared security service owned by `hermes-vault`**, with HSL as first consumer. HSL ownership of a Vault deployment is superseded for the target architecture.
3. **No conflict with ADR-006/013.** Single-node Raft and Community-first remain the baseline; this spec reinforces them.
4. **No conflict with ADR-002/011/012/015/017.** Root-out-of-Hermes, audit-before-migration, restore-drill gate, fail-closed, and explicit secret-zero design are all reinforced.
5. **ADR-018 through ADR-021 resolve §25.** Verify-only continuity, private Docker security plane, controlled parallel-run and out-of-band Shamir custody are now normative decisions.

## 24. Self-review result

- Placeholders/TODO/TBD/FIXME: none present.
- Contradictions: stale open-decision language was removed; edition, deployment, seal, ownership, network, continuity and isolation are internally aligned.
- Implementation-state wording: repository-side implementation is distinguished from live runtime state; `NOT_RUN` live gates are not promoted to PASS.
- Secret hygiene: no secret values, tokens, SecretIDs, recovery material or concrete recovery locators present.
- ADR alignment: consistent; superseded assumptions explicitly recorded without deleting history.

## 25. Structural decisions — owner resolutions

The original questions are preserved below for auditability. **This resolution records owner decisions and does not claim live implementation.** Runtime/bootstrap gates remain separately verifiable and are never inferred from these decisions.

1. **Key continuity for existing HSL-signed evidence.** The historical HSL transit key `hermes-lab-l1-signer` is non-exportable (`exportable=false`, `allow_plaintext_backup=false`). It cannot be migrated as material to the shared `hsl-transit` mount. Original options were: retain the old HSL path for verification, abandon historical verification/re-sign, or define another continuity policy.
   - **RESOLVED 2026-08-21 — ADR-018:** retain the legacy HSL Vault/key path strictly **verify-only** during the continuity window. After cutover, no new signature is created with `hermes-lab-l1-signer`. Historical evidence is not bulk re-signed; original signatures remain the provenance anchor.

2. **Network exposure model.** The original design assumed loopback/container-network TLS but left exact bind/connectivity undecided.
   - **RESOLVED 2026-08-21 — ADR-019 + ADR-019A:** host publication remains exactly `127.0.0.1:8200:8200`; consumer connectivity uses only the Docker-internal shared network `hermes-security-plane` with `internal: true` and Vault DNS alias `hermes-vault`. A second bridge, `hermes-vault-admin`, is reserved for local host administration so Docker can materialize the loopback bind; it has no consumer alias and IP masquerade is disabled. Port `8201` remains Docker-internal and no LAN/Internet publication, host networking, ingress or reverse proxy is introduced in the MVP.

3. **HSL deployment cutover vs parallel-run.** The original decision was whether `deployment/vault-lab-l1` should be decommissioned, kept read-only, or run in parallel.
   - **RESOLVED 2026-08-21 — ADR-020:** use a controlled **parallel-run**. The shared Vault is tested without becoming authoritative; after all acceptance gates pass, it becomes the sole signer for new evidence and the legacy deployment becomes verify-only. Retirement occurs only after the continuity/retention gate.

4. **Recovery material custody.** The original design required out-of-band custody but left the concrete location owner-decided.
   - **RESOLVED 2026-08-21 — ADR-021:** keep **Shamir 3/2** with three independent out-of-band custody locations. The concrete location and identifying metadata of each share are intentionally never recorded in GitHub, Hermes or Jarvas. Generation/distribution/use remain HITL.

5. **Exact image version and registry.** The original design required official `hashicorp/vault` pinned by digest.
   - **RESOLVED 2026-08-21:** MVP uses `hashicorp/vault:1.21.4@sha256:4e33b126a59c0c333b76fb4e894722462659a6bec7c48c9ee8cea56fccfd2569` from the official registry. No internal mirror is introduced for the MVP; changing registry/version requires a separately verified change.
