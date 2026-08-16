# Phase 0 Discovery & Prerequisites Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a deterministic, read-only and secret-safe discovery collector for the Jarvas/Hermes host that produces the sanitized evidence required by EPIC-00 without installing Vault or exposing credential values.

**Architecture:** A Python standard-library collector executes only a closed allowlist of local read-only probes with bounded timeouts. It converts raw command output immediately into typed/sanitized metadata, never persists raw environment/config content, and emits a versioned JSON report plus a derived secret-reference inventory containing names/paths/consumers only. A separate validator enforces the Phase 0 evidence contract and fail-closes when required observations are missing.

**Tech Stack:** Python 3.12 standard library, `unittest`, JSON, POSIX/Linux commands (`uname`, `systemctl`, `docker`, `ss`, `df`, `openssl`) when available.

## Global Constraints

- Read-only discovery only; no package install, service restart, Docker mutation, file mutation or network mutation.
- Never emit secret/token/password/key/cookie values, raw environment dumps, private-key material or command output that may contain them.
- Never use `env`, `printenv`, `docker inspect` without a constrained format, `systemctl show` without selected properties, or recursive config-file content dumps.
- Command execution uses argv lists, no `shell=True`, bounded timeout and bounded captured output.
- Permission-denied/not-installed states are explicit observations, never silently converted to PASS.
- Output file, when requested, is created atomically with mode `0600`.
- Phase 0 does not install Vault and cannot advance P1 automatically.
- Canonical P0 gates remain: `DISCOVERY_COMPLETE`, `NO_SECRET_IN_REPO`, `TARGET_ARCHITECTURE_APPROVED`, `RECOVERY_DESIGN_DEFINED`.

---

### Task 1: Tests-first sanitization and execution contract

**Files:**
- Create: `tests/test_phase0_discovery.py`
- Create: `tools/phase0_discovery.py`

**Interfaces:**
- Produces `run_command(argv: list[str], timeout_s: float = 5.0) -> CommandObservation`.
- Produces `sanitize_text(text: str) -> str` for defensive final-output filtering only; collectors must avoid collecting secret values in the first place.
- Produces `write_report_atomic(path: Path, report: dict) -> None` with final mode `0600`.

- [ ] Write tests proving subprocesses use argv/no shell, timeouts are bounded, output is size-bounded, common bearer/token/password/private-key patterns are redacted, and output mode is `0600`.
- [ ] Run tests and confirm RED because implementation does not yet exist.
- [ ] Implement minimal command/sanitization primitives.
- [ ] Re-run tests to GREEN and commit.

### Task 2: Host/runtime inventory collectors

**Files:**
- Modify: `tools/phase0_discovery.py`
- Modify: `tests/test_phase0_discovery.py`

**Interfaces:**
- Produces `collect_host()`, `collect_storage()`, `collect_systemd()`, `collect_docker()`, `collect_listeners()` returning JSON-serializable metadata only.

- [ ] Add failing tests with synthetic command responses for Debian/kernel/CPU, filesystem capacity, selected systemd unit properties, Docker server/client version and constrained container fields, and bounded listening-socket metadata.
- [ ] Implement collectors with explicit `available`, `status`, `reason`, and `observed_at` fields.
- [ ] Prove Docker/systemd collectors never request environment variables or full inspect payloads.
- [ ] Run targeted tests to GREEN and commit.

### Task 3: Secret-reference and identity inventory without values

**Files:**
- Modify: `tools/phase0_discovery.py`
- Modify: `tests/test_phase0_discovery.py`
- Modify: `templates/secret-inventory.yaml`

**Interfaces:**
- Produces `collect_secret_references(paths: list[Path]) -> list[dict]` that may extract variable/key names and reference locations but never values.
- Produces `classify_reference(name: str, source: str) -> str` with one of `static`, `dynamic`, `pki`, `transit`, `bootstrap`, `unknown`.

- [ ] Add fixtures containing realistic `.env`, Compose and systemd EnvironmentFile references with synthetic secret values.
- [ ] Assert generated inventory includes only variable/key names, source paths, consumer hints, classification and accessibility state.
- [ ] Assert every synthetic value is absent from serialized report.
- [ ] Implement reference-only parsing and update template fields to match the generated metadata contract.
- [ ] Run targeted tests to GREEN and commit.

### Task 4: TLS, Vault prerequisites and recovery observations

**Files:**
- Modify: `tools/phase0_discovery.py`
- Modify: `tests/test_phase0_discovery.py`

**Interfaces:**
- Produces `collect_tls_metadata(paths: list[Path])`, `collect_vault_prerequisites()`, and `collect_recovery_constraints()`.

- [ ] Add failing tests for certificate metadata extraction that never reads/prints private-key content.
- [ ] Add failing tests for Vault binary presence/version observation, Docker capability, storage suitability and recovery-path metadata.
- [ ] Implement probes; no Vault install/init/unseal command exists in Phase 0 code.
- [ ] Run targeted tests to GREEN and commit.

### Task 5: Versioned report, P0 evaluator and CLI

**Files:**
- Modify: `tools/phase0_discovery.py`
- Create: `tools/validate_phase0.py`
- Create: `tests/test_phase0_validation.py`

**Interfaces:**
- CLI: `python tools/phase0_discovery.py [--output PATH] [--pretty]`.
- Validator: `python tools/validate_phase0.py REPORT.json`.
- Report schema marker: `hermes-vault-phase0-discovery/v1`.

- [ ] Add RED tests for stable report shape, deterministic gate evaluation and fail-closed missing/inconclusive observations.
- [ ] Implement CLI and validator.
- [ ] Gate evaluator may mark `DISCOVERY_COMPLETE` only when mandatory host/runtime/storage/TLS/Vault-prerequisite observations are conclusive; the other three P0 gates remain evidence/decision fields and are not guessed.
- [ ] Run all tests to GREEN and commit.

### Task 6: Runbook, CI and repository secret-safety gate

**Files:**
- Create: `docs/16-phase0-discovery-runbook.md`
- Create: `.github/workflows/ci.yml`
- Modify: `IMPLEMENTATION-CHECKLIST.md`

**Interfaces:**
- CI runs unit tests and a repository secret-pattern guard on synthetic test data allowlists only.

- [ ] Document exact Jarvas execution command, expected output, artifact handling, rollback (`rm` report only), and explicit prohibition on pasting raw secrets into issues/chat.
- [ ] Add CI for Python 3.12 `unittest` and compile checks.
- [ ] Update checklist only for repository implementation steps actually completed; do not mark live discovery gate PASS.
- [ ] Run CI and fix causal failures only.

### Task 7: Exact-head PR closure and live handoff

**Files:**
- No production changes unless verification identifies a causal fix.

- [ ] Open PR linked to #2 and record tests-first/green evidence.
- [ ] Require CI GREEN on the exact PR head.
- [ ] Merge only verified head.
- [ ] Verify post-merge CI on `main`.
- [ ] Do not close #2: live Jarvas execution is still required.
- [ ] Once Hermes/control-plane or direct host execution is available, run the collector, validate the sanitized report, update #2 with evidence metadata only, then evaluate P0 gates.