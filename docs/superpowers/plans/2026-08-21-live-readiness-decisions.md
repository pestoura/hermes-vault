# Hermes Vault Live-Readiness Decisions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the approved §25 structural decisions in `hermes-vault`, implement the safe repository-side network/TLS contract needed for the shared Vault service, and leave all secret-bearing/live bootstrap operations behind explicit HITL gates.

**Architecture:** Keep the Vault API host publication restricted to `127.0.0.1:8200` for local operator access and add one Docker-internal shared security-plane network named `hermes-security-plane`, with Vault reachable by the stable internal DNS alias `hermes-vault`. Preserve historical HSL signature verification by freezing the legacy HSL Vault path to verify-only during a controlled parallel-run transition; the shared Vault becomes the only signer for new evidence after acceptance. Shamir remains manual 3/2; concrete recovery-share storage locations are intentionally never recorded in Git/Hermes/Jarvas and are handled out-of-band by independent custodians.

**Tech Stack:** Docker Compose, HashiCorp Vault Community/OSS 1.21.4 pinned by digest, Bash/OpenSSL operator-only TLS provisioning, Python/pytest static contract tests, Markdown ADR/runbooks.

**Spec:** `docs/specs/2026-08-18-hermes-shared-vault-service-design.md`

## Global Constraints

- Base exactly on `main` merge `4ab9bf96c370add8a19f56761746afe8d55a43e1`.
- Never start Vault, create/start a container, initialize/unseal Vault, handle root/Vault tokens, Shamir shares, SecretIDs, AppRole credentials, or TLS private key material in unattended execution.
- No real secret material in repository, CI, logs, evidence, or comments.
- Keep host publication restricted to `127.0.0.1:8200:8200`; no `0.0.0.0` host bind and no LAN/Internet exposure.
- Shared Docker network is exactly `hermes-security-plane`, `internal: true`; Vault internal alias is exactly `hermes-vault`.
- HSL legacy signer becomes verify-only during transition; no new signing with the legacy key after cutover. Historical signatures are never bulk re-signed as a substitute for continuity.
- Shared Vault becomes authoritative for new HSL signing only after audit/restore/isolation/live acceptance gates pass.
- Shamir remains 3 shares / threshold 2. Concrete custody location metadata is intentionally out-of-band and must not be committed.
- `pestoura/hermes-security-labs` is not mutated by this plan.
- `VaultCredentialProvider` / PR #18 remains deferred.
- GREEN/PASS repository gates may continue automatically; stop before any live/HITL operation.

---

## Task 1 — Decision contract tests (TDD RED)

**Files:**
- Create: `tests/plans/test_live_readiness_decisions.py`

**Produces:** Static assertions for ADR-018 through ADR-021, resolved §25 markers, key-continuity/parallel-run semantics, recovery-custody non-disclosure, Compose private-network contract, and TLS SAN contract.

- [ ] Create tests that require:
  - `ADR-018` with `verify-only`, legacy key continuity and no re-signing;
  - `ADR-019` with `hermes-security-plane`, `internal: true`, `127.0.0.1:8200`, alias `hermes-vault`;
  - `ADR-020` with controlled parallel-run and new shared Vault authoritative for new signatures only after acceptance;
  - `ADR-021` with Shamir 3/2, independent out-of-band custody and prohibition on recording concrete custody locations in Git/Hermes/Jarvas;
  - spec §25 resolution markers for items 1–5;
  - Compose network declaration/attachment/alias while preserving loopback publication;
  - operator TLS provisioning script to include SANs for `DNS:hermes-vault`, `DNS:localhost`, `IP:127.0.0.1` and retain HITL refusal.
- [ ] Run only this new test file on the exact base and record expected RED failures.
- [ ] Commit tests before implementation/config changes.

## Task 2 — ADR/spec resolution (minimal GREEN part A)

**Files:**
- Modify: `docs/13-security-decisions.md`
- Modify: `docs/specs/2026-08-18-hermes-shared-vault-service-design.md`

**Produces:** Auditable resolution of previously open structural decisions without rewriting historical rationale.

- [ ] Add ADR-018: HSL historical signature continuity via legacy verify-only retention; reject bulk historical re-signing.
- [ ] Add ADR-019: private shared Docker security plane with loopback-only host publication.
- [ ] Add ADR-020: controlled parallel-run/cutover; shared Vault signs new evidence only after acceptance; legacy Vault verify-only, then retirement per retention.
- [ ] Add ADR-021: manual Shamir 3/2 with three independent out-of-band custody locations; exact custody locators intentionally absent from repository/system context.
- [ ] In spec §25 preserve each original decision question and append a dated `RESOLVED 2026-08-21` resolution. Mark image version as already resolved to the pinned Community image/digest. Do not claim runtime implementation.
- [ ] Run decision-contract tests; documentation assertions should become GREEN while Compose/TLS assertions remain RED.
- [ ] Commit documentation resolution separately.

## Task 3 — Private security-plane network (minimal GREEN part B)

**Files:**
- Modify: `deployments/vault/docker-compose.yml`
- Modify: `tests/baseline/test_compose_architecture.py` only if an existing generic assertion needs extension; do not weaken prior controls.

**Produces:** Stable private container-to-container endpoint for consumers without LAN publication.

- [ ] Add service network attachment to `hermes-security-plane` with alias `hermes-vault`.
- [ ] Add top-level network declaration:

```yaml
networks:
  hermes-security-plane:
    name: hermes-security-plane
    internal: true
```

- [ ] Preserve `127.0.0.1:8200:8200` exactly.
- [ ] Do not add extra published ports, ingress, reverse proxy, host networking, macvlan, or external exposure.
- [ ] Run decision-contract + baseline Compose tests.
- [ ] Run `docker compose config` when canonical Jarvas execution is available; do not run `up`, `create`, or `start`.
- [ ] Commit the network change.

## Task 4 — TLS internal-name contract (minimal GREEN part C)

**Files:**
- Modify: `deployments/vault/scripts/provision-tls.sh`
- Modify: `tests/baseline/test_tls_material.py` if necessary to make the SAN requirement explicit without generating any certificate.

**Produces:** Future HITL-generated local server certificate that validates both loopback operator access and internal Docker DNS access.

- [ ] Keep `VAULT_TLS_OPERATOR_ACK=yes` mandatory.
- [ ] Keep key generation operator-only; do not execute the script.
- [ ] Add an OpenSSL extension file/config generated in the git-ignored output directory or pass a safe SAN extension to certificate signing so the resulting certificate includes exactly the minimum required names: `DNS:hermes-vault`, `DNS:localhost`, `IP:127.0.0.1`.
- [ ] Remove the temporary CSR/extension file after certificate creation; do not echo private material.
- [ ] Keep key permissions `0600`.
- [ ] Run static TLS tests only; never generate TLS material in CI/unattended gates.
- [ ] Commit TLS contract change.

## Task 5 — Transition runbook and migration boundary

**Files:**
- Create: `docs/runbooks/hsl-key-continuity.md`
- Modify: `docs/runbooks/hsl-decommission.md`
- Modify: `docs/plans/hsl-consumer-migration-boundary.md`

**Produces:** Operationally unambiguous transition states while keeping HSL repository untouched.

- [ ] Define transition states:
  - `LEGACY_SIGN_ACTIVE` (current historical pre-cutover state only);
  - `PARALLEL_SHARED_PENDING_ACCEPTANCE` (shared service testing; legacy unchanged);
  - `SHARED_SIGN_ACTIVE_LEGACY_VERIFY_ONLY` (target transition state);
  - `LEGACY_VERIFY_RETIRED` (only after retention/continuity owner gate).
- [ ] Define acceptance prerequisites for entering `SHARED_SIGN_ACTIVE_LEGACY_VERIFY_ONLY`: Vault health/unseal, audit PASS, restore drill PASS, HSL isolation/negative capability PASS, TLS connectivity PASS, signer sign/verify PASS, evidence verification of both legacy historical signatures and new shared signatures.
- [ ] Explicitly forbid new legacy signing after cutover and forbid bulk historical re-signing as a continuity substitute.
- [ ] State that actual HSL configuration changes are a separate cross-repo change and are NOT executed here.
- [ ] Run documentation contract tests.
- [ ] Commit runbook changes.

## Task 6 — Verification, review, CI, integration

**Files:** no intended production changes unless a test exposes a defect.

- [ ] Fresh targeted tests for decision/network/TLS/runbooks.
- [ ] `pytest tests/ -m 'not hitl'`.
- [ ] `scripts/ci/run-gates.sh --scan-only`.
- [ ] `scripts/ci/run-gates.sh --dry`.
- [ ] Full gate only if its current contract is proven offline/no-live; otherwise record `NOT_RUN_REQUIRES_LIVE_HITL_VAULT`.
- [ ] `docker compose config` only; never start/create container.
- [ ] `git diff --check`.
- [ ] Tracked-tree gitleaks/secret scan with no weakening of allowlists/baselines.
- [ ] Full exact-SHA diff review for Critical/Important/Minor.
- [ ] Push/open PR; require exact-head hosted CI if available.
- [ ] With all required repository-side PRIMARY gates fresh GREEN and no blocking review finding, merge under the standing GREEN/PASS authorization using expected-head SHA lock.
- [ ] Post-merge verify `main` contains ADRs, network/alias/SAN contract and rerun safe repository-side gates.
- [ ] Stop before live Vault start/bootstrap and record remaining HITL gate: TLS key generation/custody, init/unseal/root, audit live, snapshot/live restore, HSL mount/key/AppRole/SecretID activation and cross-repo migration.

## Acceptance State

This plan may declare `LIVE_READINESS_REPO_SIDE_PASS` only if all safe repository-side gates above execute successfully on the exact merged tree. It must never infer or declare `VAULT_HEALTH_PASS`, `VAULT_UNSEALED`, `AUDIT_PASS`, `SNAPSHOT_PASS`, `ROOT_REVOKED`, HSL live signing acceptance, or production readiness from static tests.
