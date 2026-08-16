# EPIC-02 Workload Identity, Policies & KV Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare the repository-safe identity, least-privilege policy and KV v2 contracts required for EPIC-02 without selecting or migrating a real Jarvas secret before live discovery evidence exists.

**Architecture:** AppRole remains the initial workload authentication mechanism. A versioned identity manifest defines bounded roles for `hermes-runtime`, `hermes-controller`, `jarvas-operations` and the first tool identity `github-tool`. Policies are explicit and path-exact: runtime/controller/operations receive self-introspection only, while `github-tool` may read exactly `secret/data/jarvas/github/runtime` and its exact metadata path. A bootstrap script configures the KV v2 mount, policies and AppRoles under the controlled bootstrap-root phase, but never creates a real secret or accepts secret values on argv. A policy linter and negative capability matrix provide repository-side proof of no `sudo`, no global wildcard and no cross-tool KV access.

**Tech Stack:** Vault Community 1.21.4 CLI, AppRole, KV v2, HCL ACL policies, JSON manifests, Python 3.12 standard library/unittest, Bash.

## Global Constraints

- Parent baseline is stacked on EPIC-01 head `27be0d124fa6d3bb6fd34f44d76ec44a8266eb56`.
- AppRole is the initial auth method; certificate/JWT/Kubernetes auth remain later upgrades.
- Every workload/tool has its own role and policy; no shared global workload credential.
- `token_no_default_policy=true` for all roles.
- `secret_id_num_uses=1`; `secret_id_ttl=10m`; response wrapping TTL `5m`.
- Normal workload token TTLs are bounded to 10–15m with max TTL <=30m.
- No policy may contain `sudo`, root-protected admin paths, `path "*"`, `path "+/*"`, `secret/*`, or cross-tool KV access.
- `hermes-runtime` and `hermes-controller` do not receive direct KV read access in this EPIC.
- First tool identity is `github-tool`, but this does not select GitHub as the real migration pilot.
- KV v2 is mounted at `secret/`; canonical first tool path is `secret/data/jarvas/github/runtime` with metadata at `secret/metadata/jarvas/github/runtime`.
- No real secret value is committed, generated, copied, migrated, rotated or revoked in repository implementation.
- `KV_PILOT_PASS`, `ROTATION_PASS`, `LEGACY_SECRET_REMOVED` and `RESTART_PASS` remain `NOT_RUN` until live inventory identifies a low-risk pilot with owner/rollback/acceptance evidence.

---

### Task 1: Versioned workload identity manifest

**Files:**
- Create: `identity/workload-roles.json`
- Create: `tools/validate_identity_contract.py`
- Create: `tests/test_epic02_identity_kv.py`

**Interfaces:**
- Manifest schema: `hermes-vault-workload-identities/v1`.
- Roles: `hermes-runtime`, `hermes-controller`, `jarvas-operations`, `github-tool`.
- Validator: `validate_identity_contract(data: dict) -> tuple[bool, list[str]]`.

- [ ] Write failing tests requiring the four exact identities, unique policies, AppRole, bounded TTLs, single-use SecretIDs, wrapping TTL and `token_no_default_policy=true`.
- [ ] Run tests and confirm RED because manifest/validator do not exist.
- [ ] Implement manifest and validator; reject duplicate policy identity, unlimited TTL/uses, admin/JIT/root identities and unknown roles.
- [ ] Re-run targeted tests to GREEN and commit.

### Task 2: Minimal policies and policy linter

**Files:**
- Create: `identity/policies/hermes-runtime.hcl`
- Create: `identity/policies/hermes-controller.hcl`
- Create: `identity/policies/jarvas-operations.hcl`
- Create: `identity/policies/github-tool.hcl`
- Create: `tools/lint_vault_policies.py`
- Modify: `tests/test_epic02_identity_kv.py`

**Interfaces:**
- Self-introspection paths: `auth/token/lookup-self` read and `sys/capabilities-self` update.
- `github-tool`: exact read on `secret/data/jarvas/github/runtime` and exact metadata read on `secret/metadata/jarvas/github/runtime`.
- Linter: `lint_policy_text(name: str, text: str) -> list[str]`.

- [ ] Write RED tests proving runtime/controller/operations have no `secret/data/` access and github-tool cannot access any Microsoft/Grafana/Cloudflare path.
- [ ] Add linter tests rejecting `sudo`, root policy concepts, global/catch-all wildcards, `secret/*`, auth/policy/mount administration and wildcard KV paths.
- [ ] Implement exact HCL policies and conservative text linter.
- [ ] Re-run targeted tests to GREEN and commit.

### Task 3: KV v2/bootstrap operations without values

**Files:**
- Create: `operations/epic02_identity_kv.sh`
- Modify: `tests/test_epic02_identity_kv.py`

**Interfaces:**
- Commands: `preflight`, `kv-status`, `kv-enable`, `configure-policies`, `configure-roles`, `role-id ROLE`, `wrapped-secret-id ROLE`, `capability-check ROLE`.
- No command for `kv put`, secret migration, rotation or legacy deletion.

- [ ] Write RED tests requiring Vault CLI 1.21.4, HTTPS/CA, initial-root guard for configuration, exact KV v2 mount verification, policy writes and bounded AppRole creation.
- [ ] Require `vault secrets enable -path=secret -version=2 kv` only when absence is proven; a non-KV-v2 existing `secret/` mount fails closed.
- [ ] Require RoleID reads and response-wrapped SecretID issuance without credentials on argv.
- [ ] Implement script and negative capability checks via `vault token capabilities`/self-authenticated role sessions; no secret data is created.
- [ ] Run Bash syntax and targeted tests to GREEN and commit.

### Task 4: Negative capability matrix and pilot handoff contract

**Files:**
- Create: `identity/negative-capability-matrix.json`
- Create: `templates/kv-pilot-handoff.json`
- Create: `docs/18-epic02-identity-kv-runbook.md`
- Modify: `tests/test_epic02_identity_kv.py`

**Interfaces:**
- Negative matrix enumerates expected `deny` paths for each identity.
- Pilot handoff schema: `hermes-vault-kv-pilot-handoff/v1` with reference metadata only.

- [ ] Write RED tests requiring cross-tool denies, admin-path denies and no secret values in the pilot template.
- [ ] Implement matrix for all four roles; include positive paths separately from negative probes.
- [ ] Implement pilot handoff fields: inventory_id, owner, consumer, provider, classification, target_path, acceptance_test_ref, rollback_ref, legacy_reference, rotation_supported, status.
- [ ] Set template status `AWAITING_LIVE_DISCOVERY`; never preselect a real credential.
- [ ] Document live sequence: inventory → human/owner validation → write to KV → consumer cutover → positive/negative test → temporary rollback window → rotate legacy → restart → remove legacy → secret scan/evidence.
- [ ] Run targeted tests to GREEN and commit.

### Task 5: Repository acceptance and stacked PR

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `IMPLEMENTATION-CHECKLIST.md`

- [ ] Extend CI with identity validator, policy linter, shell syntax and full test suite.
- [ ] Run local combined suite (EPIC-00 + EPIC-01 + EPIC-02), compileall and Bash syntax.
- [ ] Open stacked draft PR against `epic-01/baseline-adoption`, linked to #4.
- [ ] If GitHub hosted runners remain billing-blocked, record `BLOCKED_EXTERNAL_BILLING`; do not call it PASS and do not merge.
- [ ] Keep #4 open: live `AUTH_PASS`, capability negative tests, KV pilot, rotation/removal and restart evidence remain required.