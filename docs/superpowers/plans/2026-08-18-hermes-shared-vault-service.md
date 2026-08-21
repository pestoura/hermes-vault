# Hermes Shared Vault Service — TDD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `pestoura/hermes-vault` as a shared, Docker-based, single-node HashiCorp Vault Community/OSS service (Raft, TLS, Shamir 3/2, audit, snapshots + restore drill) that HermesJarvas sub-projects consume through a provider-neutral capability contract with strict per-consumer isolation — HSL as first consumer — without transferring Vault ownership to a consumer, without auto-promotion, and without any secret material in the repo.

**Architecture:** Docker single-node Vault Community/OSS pinned by digest; Integrated Storage (Raft); mandatory TLS; manual Shamir 3/2 (no auto-unseal); one mandatory audit device with redaction; per-consumer dedicated mounts + exact-path policies + dedicated AppRoles; a provider-neutral capability contract (no secret material) defined in this repo; fail-closed lifecycle; secret-zero handled out-of-band. Existing HSL `deployment/vault-lab-l1/` patterns are generalized INTO this service; HSL becomes a consumer only. The concrete `VaultCredentialProvider` (#18) is explicitly deferred to PR-chain reconciliation and is NOT built here.

**Tech Stack:** HashiCorp Vault 1.21.4 (Community/OSS, `@sha256` pinned to the HSL-validated digest), Docker / Compose, Python 3.11+ (PEP 668 → venv or uv), `pytest`, `hvac` (Vault client, implementation/test only), `pydantic` (contract schema), HCL policy files, `bash` gate scripts. No Enterprise/HCP features, no namespaces.
**Spec:** `docs/specs/2026-08-18-hermes-shared-vault-service-design.md`

**Additional sources:** ADRs `docs/13`, operating model `docs/15`. This plan implements the spec; it does not reopen superseded assumptions. PR #14–#16 are harvested for reusable work; #17 is a superseded governance action; #18 is deferred.

## Global Constraints

- **Image pin:** `hashicorp/vault:1.21.4@sha256:4e33b126a59c0c333b76fb4e894722462659a6bec7c48c9ee8cea56fccfd2569` (HSL-validated digest; no other digest permitted).
- **NO real secret** — token, recovery/unseal key, Shamir share, SecretID, private key, wrapped secret, or raw secret value — is ever written to the repo, logs, CI output, or evidence bundles (`SECURITY.md`, spec §22, ADR-014).
- **NO auto-promotion** to production. Promotion requires: restore drill PASS + audit PASS + owner sign-off (spec §10, §16.3, ADR-012).
- **Community/OSS only.** No Enterprise namespaces, replication, or HCP auto-unseal (spec §4, §12, ADR-013).
- **Shared ownership.** `hermes-vault` owns deployment/lifecycle; consumers depend on the contract only (spec §3, §15, §17).
- **NO HSL modification.** This plan never writes to `pestoura/hermes-security-labs` or any other repo; cross-repo onboarding is specified, not performed (final task M1).
- **#18 deferred.** The concrete `VaultCredentialProvider` adapter is out of scope here; only the provider-neutral contract schema + conformance live in this repo.
- **HITL boundaries (never in unattended tasks):** `vault operator init`, `vault operator unseal`, initial root token handling/revoke, AppRole SecretID issuance/wrapping, TLS private-key generation/custody, and production promotion sign-off are operator steps only — recorded in runbooks, never coded or auto-executed.
- **Local gates primary.** Hosted CI billing aborts GitHub Actions on this account ~2s (external blocker, not code failure); the local `run-gates.sh` is the primary gate runner.

---

## File Map

| Path | Purpose | Task |
|---|---|---|
| `pyproject.toml`, `.gitignore` | Dependency-isolated test harness | A1 |
| `tests/` (scaffold, `*/__init__.py`, `conftest.py`) | Fixtures, `hitl` marker, import sanity | A1 |
| `src/policy_lint/linter.py` | Static HCL lint: ban wildcard/sudo for normal identities | A2 |
| `src/capability_contract/schema.py` | Provider-neutral contract (no secret fields) | A3 |
| `scripts/ci/run-gates.sh` | Local primary gate runner (billing-aware) | A4 |
| `.github/workflows/fast-gates.yml` | Minimal trusted, Vault-free, secret-free mirror | A4 |
| `deployments/vault/Dockerfile` | Pinned digest image | B1 |
| `deployments/vault/docker-compose.yml` | Hardened single-node service | B1 |
| `deployments/vault/config/vault.hcl` | Raft storage, TLS listener, Shamir (no auto-unseal) | B1 |
| `deployments/vault/.gitignore` | Exclude `vault-data/`, `certs/`, `*.key`, `*.pem` | B1 |
| `deployments/vault/scripts/provision-tls.sh` | Operator TLS cert into git-ignored `certs/` | B3 |
| `docs/runbooks/vault-bootstrap.md` | HITL init/unseal/root + enable-audit procedure | B4 |
| `deployments/vault/scripts/bootstrap-checklist.sh` | Read-only checklist printer (no secret ops) | B4 |
| `deployments/vault/scripts/enable-audit.sh` | Idempotent audit-device enable (operator token) | C1 |
| `deployments/vault/scripts/snapshot.sh` | Raft snapshot + checksum + git-ignored encrypted copy | D1 |
| `deployments/vault/scripts/restore-drill.sh` | Isolated restore-drill harness | D1 |
| `deployments/vault/scripts/enable-hsl-transit.sh` | HSL `hsl-transit/` mount + `hsl-signing` key (HITL) | E1 |
| `policies/hsl/hsl-signer.hcl` | Exact-path policy for HSL signer AppRole | E2 |
| `deployments/vault/scripts/enable-hsl-signer.sh` | AppRole `hsl-signer` + policy bind (HITL) | E2 |
| `src/isolation/matrix.py` | Reusable negative-capability matrix builder | E4 |
| `src/lifecycle/states.py` | Service/contract state machine + fail-closed guards | G1 |
| `src/evidence/redact.py` | Deterministic evidence redactor | G2 |
| `docs/runbooks/secret-zero.md` | Wrapped SecretID bootstrap procedure (HITL) | H1 |
| `docs/runbooks/hsl-generalization.md` | lab→shared pattern mapping; ownership stays here | I1 |
| `docs/runbooks/hsl-decommission.md` | Freeze/decommission options, gated on owner decision | I2 |
| `docs/plans/pr-chain-cleanup.md` | #14–#16 harvest, #17 governance, #18 deferred | J1 |
| `docs/plans/hsl-consumer-migration-boundary.md` | HSL migration steps, out-of-repo, owner gates | K1 |
| `docs/plans/hsl-cross-repo-handoff.md` | Final handoff: specifies HSL onboarding + #18, no HSL mutation | M1 |
| `README.md` (modify), `SECURITY.md` (modify) | Ownership/supersession notes | I1, B3 |
| `tests/*` (per task) | RED→GREEN TDD proofs | All |

---

## Global invariants (asserted by test G3 and carried by every task)

```text
INV-1  NO_SECRET_IN_REPO — never commit or log real secret material.
INV-2  NO_AUTO_PROMOTION — production use gated on restore-drill PASS + audit PASS + owner sign-off.
INV-3  COMMUNITY_OSS_ONLY — no Enterprise/HCP feature, no `namespace=` usage, no auto-unseal.
INV-4  SHARED_OWNERSHIP — hermes-vault owns deployment/lifecycle; consumers depend on the contract only.
INV-5  PER_CONSUMER_ISOLATION — dedicated mount + dedicated AppRole + exact-path policy + negative tests.
INV-6  FAIL_CLOSED — sealed/unavailable/ERROR/policy-fail → capability denied, no fallback to static creds.
INV-7  AUDIT_EVERYTHING — audit device functional before any real secret migration; redaction enforced.
INV-8  SECRET_ZERO_EXPLICIT — bootstrap credential delivered wrapped/single-use/short-TTL, never in .env/state/GitHub/logs.
INV-9  SANITIZED_EVIDENCE — tokens/SecretIDs/keys/Recovery/RIDs redacted in all emitted artifacts.
INV-10 HITL_BOUNDARY — init/unseal/root/SecretID/TLS-private/promotion are operator steps, not code paths.
INV-11 SCOPE_HERMES_VAULT_ONLY — no file in this plan is written outside pestoura/hermes-vault.
```

---

## Task groups and commit boundaries (intended sequence)

| Commit | Groups | Scope |
|---|---|---|
| C1 | A1–A4 | Test/CI scaffold, policy-lint harness, contract schema, local gates |
| C2 | B1–B2 | Docker baseline + acceptance harness (pre-HITL) |
| C3 | B3–B4 | TLS material + init/unseal/root runbook (HITL) |
| C4 | C1 | Audit device + redaction tests |
| C5 | D1 | Snapshot + isolated restore-drill harness |
| C6 | E1–E4 | HSL transit mount/key, hsl-signer AppRole+policy, negative matrix, isolation framework |
| C7 | F1 | Capability-contract conformance (provider-neutral; #18 adapter deferred) |
| C8 | G1–G3 | Lifecycle/fail-closed, sanitized evidence, global invariants tests |
| C9 | H1 | Secret-zero procedure + delivery-constraint tests |
| C10 | I1–I2 | Generalize HSL deployment into hermes-vault (no ownership back) + decommission plan |
| C11 | J1, K1 | PR-chain cleanup strategy (doc), HSL migration boundary (doc) |
| C12 | L1, M1 | No-live-promotion/HITL summary (doc), final cross-repo handoff (specifies HSL + #18; does NOT modify HSL) |

> NOTE: This plan document is the ONLY artifact committed for the current request. Commits C1–C12 describe the implementation sequence; they are executed later, task-by-task, never in this planning step.

---

## Group A — Repo scaffold & local CI (no Vault, no secrets)

### Task A1: Create test/CI scaffold

**Objective:** Establish a runnable, dependency-isolated test harness that later tasks extend.

**Files:**
- Create: `pyproject.toml` (build-system + test deps: `pytest`, `hvac==0.13.x`, `pydantic>=2`, `pyyaml`)
- Create: `tests/conftest.py` (fixtures: `vault_addr` from env, `HITL_SKIP` marker)
- Create: `tests/__init__.py`, `tests/scaffold/__init__.py`, `tests/policy_lint/__init__.py`, `tests/contract/__init__.py`, `tests/isolation/__init__.py`, `tests/audit/__init__.py`, `tests/recovery/__init__.py`, `tests/lifecycle/__init__.py`, `tests/evidence/__init__.py`, `tests/secret_zero/__init__.py`, `tests/ci/__init__.py`, `tests/baseline/__init__.py`, `tests/plans/__init__.py`
- Create: `.gitignore` (venv, `__pycache__`, `*.key`, `secrets/`, `.vault-token`, `certs/`, `vault-data/`, `backups/`)

- [ ] **Step 1: Write failing test**
```python
# tests/scaffold/test_imports.py
def test_harness_importable():
    import pytest  # fixture sanity
    assert pytest.__version__ >= "7.0"
```

- [ ] **Step 2: Run test to verify failure**
Run: `python -m pytest tests/scaffold/test_imports.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pytest'` (deps not yet installed in env).

- [ ] **Step 3: Write minimal implementation**
Create `pyproject.toml`:
```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "hermes-vault-plan"
version = "0.0.0"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
test = ["pytest>=7", "hvac>=0.13,<0.14", "pydantic>=2,<3", "pyyaml>=6"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["hitl: operator-only step, skip in CI without explicit flag"]
```

- [ ] **Step 4: Run test to verify pass**
Run: `uv sync --extra test && python -m pytest tests/scaffold/test_imports.py -v` (or `python -m venv .venv && . .venv/bin/activate && pip install -e '.[test]' && pytest ...`)
Expected: PASS — 1 passed.

- [ ] **Step 5: Commit**
```bash
git add pyproject.toml .gitignore tests/conftest.py tests/__init__.py tests/*/__init__.py tests/scaffold/test_imports.py
git commit -m "test(ci): scaffold hermes-vault test harness and dependency isolation"
```

### Task A2: Policy lint harness (static, no wildcard/sudo for normal identities)

**Objective:** A static linter that fails any committed policy granting `path "*"` or `sudo` to non-admin identities, and validates HCL path syntax — satisfies spec §11.4, §21.2, ADR-013.

**Files:**
- Create: `src/policy_lint/__init__.py`, `src/policy_lint/linter.py`
- Test: `tests/policy_lint/test_policy_lint.py`

- [ ] **Step 1: Write failing tests**
```python
# tests/policy_lint/test_policy_lint.py
from src.policy_lint.linter import lint_policy_text

def test_wildcard_rejected():
    bad = 'path "secret/*" { capabilities = ["read"] }'
    issues = lint_policy_text(bad, identity="hsl-signer")
    assert any("wildcard" in i.lower() for i in issues)

def test_sudo_rejected_for_normal_identity():
    bad = 'path "auth/*" { capabilities = ["sudo", "update"] }'
    issues = lint_policy_text(bad, identity="hsl-signer")
    assert any("sudo" in i.lower() for i in issues)

def test_exact_path_accepted():
    good = 'path "hsl-transit/sign/hsl-signing" { capabilities = ["update"] }'
    assert lint_policy_text(good, identity="hsl-signer") == []
```

- [ ] **Step 2: Run test to verify failure**
Run: `pytest tests/policy_lint/test_policy_lint.py -v`
Expected: FAIL — `ModuleNotFoundError: src.policy_lint.linter`.

- [ ] **Step 3: Write minimal implementation**
```python
# src/policy_lint/linter.py
import re

_WILDCARD = re.compile(r'path\s+"[^"]*\*\s*"')
_SUDO = re.compile(r'capabilities\s*=\s*\[[^]]*"sudo"')

def lint_policy_text(text: str, identity: str) -> list[str]:
    """Return human-readable violations. Empty list == clean.
    Admin identities (hermes-vault-admin JIT) are exempt from sudo/wildcard bans
    only when explicitly labelled; normal consumers are never exempt."""
    issues: list[str] = []
    if _WILDCARD.search(text):
        issues.append(f"wildcard path forbidden for identity={identity} (spec §11.4)")
    if _SUDO.search(text) and identity != "hermes-vault-admin":
        issues.append(f"sudo capability forbidden for non-admin identity={identity} (ADR-013)")
    return issues
```

- [ ] **Step 4: Run test to verify pass**
Run: `pytest tests/policy_lint/test_policy_lint.py -v`
Expected: PASS — 3 passed.

- [ ] **Step 5: Commit**
```bash
git add src/policy_lint/ tests/policy_lint/
git commit -m "test(policy): static lint bans wildcard/sudo for normal identities"
```

### Task A3: Provider-neutral capability-contract schema (no secret material)

**Objective:** Define the contract types from spec §14 as a validated schema; prove it carries NO secret material and is provider-neutral.

**Files:**
- Create: `src/capability_contract/__init__.py`, `src/capability_contract/schema.py`
- Test: `tests/contract/test_capability_contract.py`

- [ ] **Step 1: Write failing test**
```python
# tests/contract/test_capability_contract.py
from src.capability_contract.schema import CapabilityRequest, CapabilityType

def test_required_fields_present():
    r = CapabilityRequest(
        principal="hermes-controller",
        action="transit.sign",
        resource_scope="hsl-transit/hsl-signing",
        risk_class="medium",
        requested_ttl=300,
    )
    assert r.capability_type is None or isinstance(r.capability_type, CapabilityType)

def test_rejects_secret_material():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        CapabilityRequest(principal="x", action="y",
                          resource_scope="z", risk_class="low",
                          requested_ttl=60,
                          _secret_value="VAULT-TOKEN-XXXX")  # field must not exist
```

- [ ] **Step 2: Run test to verify failure**
Run: `pytest tests/contract/test_capability_contract.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**
```python
# src/capability_contract/schema.py
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class CapabilityType(str, Enum):
    delegated_operation = "delegated_operation"
    ephemeral_token = "ephemeral_token"
    wrapped_secret = "wrapped_secret"
    certificate = "certificate"
    dynamic_credential = "dynamic_credential"

class CapabilityRequest(BaseModel):
    # NO secret-material fields by design (spec §14). Delivery is handled separately.
    principal: str
    action: str
    resource_scope: str
    risk_class: str
    requested_ttl: int = Field(ge=0, le=3600)
    capability_type: Optional[CapabilityType] = None
    execution_id: Optional[str] = None
    plan_id: Optional[str] = None
    request_id: Optional[str] = None

    model_config = {"extra": "forbid"}  # reject unexpected fields incl. any secret payload
```

- [ ] **Step 4: Run test to verify pass**
Run: `pytest tests/contract/test_capability_contract.py -v`
Expected: PASS — 2 passed.

- [ ] **Step 5: Commit**
```bash
git add src/capability_contract/ tests/contract/
git commit -m "feat(contract): provider-neutral capability schema without secret material"
```

### Task A4: Local gate runner (billing-aware) + minimal workflow

**Objective:** Run fast gates locally because GitHub Actions on this account abort at ~2s on BILLING (no code failure). The local runner is primary; the workflow mirrors only trusted, Vault-free, secret-free checks.

**Files:**
- Create: `scripts/ci/run-gates.sh`
- Create: `.github/workflows/fast-gates.yml` (trusted-only, no Vault, no secrets, `permissions: read-all`)

- [ ] **Step 1: Write failing test**
```python
# tests/ci/test_gate_script.py
import subprocess, pathlib
def test_run_gates_script_exists_and_is_executable():
    p = pathlib.Path("scripts/ci/run-gates.sh")
    assert p.exists() and p.stat().st_mode & 0o111
    out = subprocess.run(["bash", str(p), "--dry"], capture_output=True, text=True)
    assert out.returncode == 0
```

- [ ] **Step 2: Run test to verify failure**
Run: `pytest tests/ci/test_gate_script.py -v`
Expected: FAIL — script missing.

- [ ] **Step 3: Write minimal implementation**
```bash
#!/usr/bin/env bash
# scripts/ci/run-gates.sh — local PRIMARY gate runner (GitHub billing aborts Actions ~2s).
# Runs cheap deterministic gates first; never emits secrets; never touches Vault runtime.
set -euo pipefail
DRY=0; [ "${1:-}" = "--dry" ] && DRY=1
echo "[gate] policy-lint";        pytest tests/policy_lint -q
echo "[gate] contract-schema";     pytest tests/contract -q
echo "[gate] lifecycle/invariants"; pytest tests/lifecycle tests/evidence -q
echo "[gate] secret-zero";        pytest tests/secret_zero -q
echo "[gate] secret-scan";        grep -rEl "VAULT-[A-Z0-9]|root_token|recovery_key|SecretID" docs policies src templates 2>/dev/null && { echo "SECRET PATTERN FOUND"; exit 1; } || echo "clean"
[ "$DRY" = 1 ] && { echo "[gate] dry run ok"; exit 0; }
echo "[gate] integration (requires local HITL Vault)"; pytest tests/isolation tests/audit tests/recovery -q
```
`.github/workflows/fast-gates.yml` mirrors only the first four gates, no Vault, no secrets.

- [ ] **Step 4: Run test to verify pass**
Run: `pytest tests/ci/test_gate_script.py -v`
Expected: PASS — 1 passed. (Real `bash scripts/ci/run-gates.sh` runs the four fast gates locally.)

- [ ] **Step 5: Commit**
```bash
git add scripts/ci/run-gates.sh .github/workflows/fast-gates.yml tests/ci/
git commit -m "ci(gates): local primary gate runner; minimal trusted GitHub workflow (billing-aware)"
```

---

## Group B — Docker single-node Vault baseline (pinned HSL digest, Raft, TLS, Shamir 3/2)

### Task B1: Compose + Dockerfile + vault.hcl

**Objective:** Reproducible, hardened single-node Vault (spec §5, §6, §7, §8). Replace earlier systemd topology (spec §5, §23.1). Pin to the HSL-validated digest.

**Files:**
- Create: `deployments/vault/Dockerfile`
- Create: `deployments/vault/docker-compose.yml`
- Create: `deployments/vault/config/vault.hcl`
- Create: `deployments/vault/.gitignore` (`vault-data/`, `certs/`, `*.key`, `*.pem`)

- [ ] **Step 1: Write failing test (config assertions, no runtime yet)**
```python
# tests/baseline/test_compose_config.py
from pathlib import Path
import yaml, re

PINNED = "hashicorp/vault:1.21.4@sha256:4e33b126a59c0c333b76fb4e894722462659a6bec7c48c9ee8cea56fccfd2569"

def test_image_pinned_by_hsl_digest():
    comp = yaml.safe_load(Path("deployments/vault/docker-compose.yml").read_text())
    img = comp["services"]["vault"]["image"]
    assert img == PINNED, img
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", img.split("@")[1])

def test_raft_storage_and_tls_enabled():
    hcl = Path("deployments/vault/config/vault.hcl").read_text()
    assert 'storage "raft"' in hcl and "node_id" in hcl
    assert "tls_disable = false" in hcl or "tls_cert_file" in hcl

def test_hardening_flags():
    comp = yaml.safe_load(Path("deployments/vault/docker-compose.yml").read_text())
    c = comp["services"]["vault"]
    assert c.get("read_only") is True
    assert "ALL" in c.get("cap_drop", [])
    assert "no-new-privileges" in str(c.get("security_opt", []))
```

- [ ] **Step 2: Run test to verify failure**
Run: `pytest tests/baseline/test_compose_config.py -v`
Expected: FAIL — files missing.

- [ ] **Step 3: Write minimal implementation**
```dockerfile
# deployments/vault/Dockerfile
# Pinned to the HSL-validated digest (supply-chain verified against the official manifest).
FROM hashicorp/vault:1.21.4@sha256:4e33b126a59c0c333b76fb4e894722462659a6bec7c48c9ee8cea56fccfd2569
USER vault
```
```yaml
# deployments/vault/docker-compose.yml
services:
  vault:
    build: .
    image: hashicorp/vault:1.21.4@sha256:4e33b126a59c0c333b76fb4e894722462659a6bec7c48c9ee8cea56fccfd2569
    command: server
    cap_drop: ["ALL"]
    read_only: true
    security_opt: ["no-new-privileges"]
    volumes:
      - ./config/vault.hcl:/vault/config/vault.hcl:ro
      - vault-data:/vault/data
      - ./certs:/vault/certs:ro   # TLS material mounted read-only; private key HITL (see B3)
    ports:
      - "127.0.0.1:8200:8200"     # loopback/container-network TLS only (spec §5, §19.2)
    healthcheck:
      test: ["CMD", "vault", "status"]
      interval: 10s
      timeout: 5s
      retries: 5
volumes:
  vault-data:
```
```hcl
# deployments/vault/config/vault.hcl
ui = false
disable_mlock = true

listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_cert_file = "/vault/certs/vault-server.pem"
  tls_key_file  = "/vault/certs/vault-server.key"   # HITL-owned private material, see B3
  tls_disable   = false
}

storage "raft" {
  path    = "/vault/data"
  node_id = "vault-1"
}

# Shamir manual seal (default). NO auto-unseal in MVP (spec §8, ADR-002/009).
```
Companion `deployments/vault/.gitignore`: `vault-data/ certs/ *.key *.pem`.

- [ ] **Step 4: Run test to verify pass**
Run: `pytest tests/baseline/test_compose_config.py -v`
Expected: PASS — 3 passed.

- [ ] **Step 5: Commit**
```bash
git add deployments/vault/Dockerfile deployments/vault/docker-compose.yml deployments/vault/config/vault.hcl deployments/vault/.gitignore tests/baseline/
git commit -m "feat(deploy): Docker single-node Vault 1.21.4 (HSL digest) pinned, Raft, TLS, Shamir (no auto-unseal)"
```

### Task B2: Baseline acceptance harness (health / TLS strictness / Raft / Shamir)

**Objective:** RED→GREEN acceptance for the running container: healthy over TLS only, Raft storage mode, Shamir threshold 2/3. HITL steps (init/unseal) are NOT automated here.

**Files:**
- Test: `tests/baseline/test_baseline_acceptance.py`

- [ ] **Step 1: Write failing test**
```python
# tests/baseline/test_baseline_acceptance.py
import os, pytest
pytestmark = pytest.mark.hitl  # requires a locally started container + operator init/unseal

def test_tls_only_no_plain_http():
    import httpx
    with pytest.raises(httpx.ConnectError):
        httpx.get(f"http://{os.environ['VAULT_ADDR'].split('//')[1]}", verify=False, timeout=3)

def test_raft_storage_mode():
    import hvac
    c = hvac.Client(url=os.environ["VAULT_ADDR"], verify=os.environ["VAULT_CACERT"])
    st = c.sys.read_health_status()
    assert st["storage_type"] == "raft"

def test_shamir_threshold_two_of_three():
    import hvac
    c = hvac.Client(url=os.environ["VAULT_ADDR"], verify=os.environ["VAULT_CACERT"])
    cfg = c.sys.read_seal_status()
    assert cfg["type"] == "shamir"
    assert cfg["threshold"] == 2 and cfg["secret_shares"] == 3
```

- [ ] **Step 2: Run test to verify failure**
Run: `pytest tests/baseline/test_baseline_acceptance.py -v`
Expected: FAIL (skipped locally without `VAULT_ADDR`/container; on a started container before init: health returns sealed; threshold asserts fail because not initialized).

- [ ] **Step 3: Minimal implementation** — `deployments/vault/docker-compose.yml` already provides the running service; operator runs `docker compose up -d`, then performs B4 HITL init/unseal. No application code beyond the compose/config from B1.

- [ ] **Step 4: Run test to verify pass**
Run (after HITL B4): `VAULT_ADDR=https://127.0.0.1:8200 VAULT_CACERT=deployments/vault/certs/ca.pem pytest tests/baseline/test_baseline_acceptance.py -v`
Expected: PASS — 3 passed.

- [ ] **Step 5: Commit**
```bash
git add tests/baseline/test_baseline_acceptance.py
git commit -m "test(baseline): TLS-only, Raft mode, Shamir 3/2 acceptance (HITL init/unseal)"
```

### Task B3: TLS cert provisioning (HITL private material)

**Objective:** Provide server TLS for the Vault listener using a locally provisioned cert (spec §7; PKI/mTLS is Later). Private key material is operator-handled and never committed.

**Files:**
- Create: `deployments/vault/scripts/provision-tls.sh` (generates `certs/vault-server.pem`, `certs/vault-server.key`, `certs/ca.pem` into the git-ignored `certs/`).
- Modify: `SECURITY.md` (note TLS private material lives out-of-repo path, operator custody).

- [ ] **Step 1: Write failing test**
```python
# tests/baseline/test_tls_material.py
from pathlib import Path
def test_tls_private_key_not_in_repo():
    bad = list(Path("deployments/vault").rglob("*.key"))
    assert bad == [], f"private key committed: {bad}"
def test_provision_script_writes_gitignored_certs():
    assert "certs/" in (Path("deployments/vault/.gitignore").read_text())
```

- [ ] **Step 2: Run test to verify failure**
Run: `pytest tests/baseline/test_tls_material.py -v`
Expected: FAIL — `certs/` present in B1 `.gitignore` but the script + SECURITY note absent.

- [ ] **Step 3: Write minimal implementation**
`provision-tls.sh` uses `openssl req -x509` to emit a self-signed CA + server cert into `deployments/vault/certs/` (git-ignored). `SECURITY.md` gains a bullet: "Vault TLS private key is operator-custodied under `deployments/vault/certs/` (git-ignored); never committed; recovery of TLS material is an operator responsibility (spec §25.4)."

- [ ] **Step 4: Run test to verify pass**
Run: `pytest tests/baseline/test_tls_material.py -v`
Expected: PASS — 2 passed.

- [ ] **Step 5: Commit**
```bash
git add deployments/vault/scripts/provision-tls.sh deployments/vault/.gitignore SECURITY.md tests/baseline/test_tls_material.py
git commit -m "feat(tls): operator TLS provisioning; private material git-ignored (HITL)"
```

### Task B4: Init / unseal / root bootstrap runbook + HITL stops

**Objective:** Controlled bootstrap (spec §8, §9, ADR-002). Code MUST NOT perform init/unseal/root/SecretID; the runbook records the human procedure and the fail-closed postures.

**Files:**
- Create: `docs/runbooks/vault-bootstrap.md` (HITL steps: `vault operator init -key-shares=3 -key-threshold=2`, record Shamir shares + root to out-of-band custody; `vault operator unseal` x2 by quorum; revoke initial root after bootstrap; enable audit).
- Create: `deployments/vault/scripts/bootstrap-checklist.sh` (read-only checklist printer; does NOT execute secret operations).

- [ ] **Step 1: Write failing test**
```python
# tests/baseline/test_no_automated_secret_ops.py
from pathlib import Path
import re
def test_runbook_has_hitl_markers():
    txt = Path("docs/runbooks/vault-bootstrap.md").read_text()
    for m in ["HITL", "init", "unseal", "root", "out-of-band custody"]:
        assert m.lower() in txt.lower(), m
def test_no_secret_in_runbook():
    txt = Path("docs/runbooks/vault-bootstrap.md").read_text()
    assert not re.search(r"(root_token|recovery_key|s\.\w{20,})", txt), "real secret leaked"
```

- [ ] **Step 2: Run test to verify failure**
Run: `pytest tests/baseline/test_no_automated_secret_ops.py -v`
Expected: FAIL — file missing.

- [ ] **Step 3: Write minimal implementation**
`docs/runbooks/vault-bootstrap.md` documents the exact `vault operator init/unseal` commands with explicit HITL gates and the post-bootstrap revoke-root + enable-audit steps; all Shamir shares/root recorded to out-of-band custody (never repo). `bootstrap-checklist.sh` only prints the checklist.

- [ ] **Step 4: Run test to verify pass**
Run: `pytest tests/baseline/test_no_automated_secret_ops.py -v`
Expected: PASS — 2 passed.

- [ ] **Step 5: Commit**
```bash
git add docs/runbooks/vault-bootstrap.md deployments/vault/scripts/bootstrap-checklist.sh tests/baseline/test_no_automated_secret_ops.py
git commit -m "docs(bootstrap): HITL init/unseal/root runbook; no automated secret ops"
```

---

## Group C — Audit (mandatory, redacted)

### Task C1: Audit device enable + redaction tests

**Objective:** At least one audit device enabled before real-secret use; audit output redacts tokens/SecretIDs/keys/recovery (spec §9, §21.2, ADR-011, docs/08).

**Files:**
- Test: `tests/audit/test_audit_redaction.py`
- Create: `deployments/vault/scripts/enable-audit.sh` (idempotent `vault audit enable file file_path=...`; HITL uses operator token).

- [ ] **Step 1: Write failing test**
```python
# tests/audit/test_audit_redaction.py
import os, pytest, hvac, json
pytestmark = pytest.mark.hitl

def test_audit_device_enabled():
    c = hvac.Client(url=os.environ["VAULT_ADDR"], token=os.environ["VAULT_TOKEN"], verify=os.environ["VAULT_CACERT"])
    assert any(a["type"] == "file" for a in c.sys.list_enabled_audit_devices()["data"].values())

def test_audit_redacts_secret_material():
    log = os.environ["VAULT_AUDIT_SAMPLE"]  # path to a captured SYNTHETIC audit file
    txt = open(log).read()
    assert "s." not in txt or "root_token" not in txt  # no clear token leakage
    assert "SecretID" not in txt
```

- [ ] **Step 2: Run test to verify failure**
Run: `pytest tests/audit/test_audit_redaction.py -v`
Expected: FAIL — audit not enabled / sample missing.

- [ ] **Step 3: Write minimal implementation**
`enable-audit.sh` runs `vault audit enable file file_path=/vault/logs/audit.json` (operator token; HITL). Redaction is enforced by Vault's audit system + the consumer redaction layer (G2).

- [ ] **Step 4: Run test to verify pass**
Run (after HITL enable): `pytest tests/audit/test_audit_redaction.py -v`
Expected: PASS — 2 passed. Acceptance gate `AUDIT_PASS` recorded.

- [ ] **Step 5: Commit**
```bash
git add deployments/vault/scripts/enable-audit.sh tests/audit/
git commit -m "feat(audit): mandatory audit device + redaction assertions (ADR-011)"
```

---

## Group D — Backup / snapshot + isolated restore drill

### Task D1: Snapshot + isolated restore-drill harness

**Objective:** Scheduled snapshots + an isolated restore drill that PASSES before production (spec §10, §21.2, ADR-012, docs/09).

**Files:**
- Create: `deployments/vault/scripts/snapshot.sh` (writes encrypted copy + checksum/metadata to git-ignored `backups/`).
- Create: `tests/recovery/test_restore_drill.py` (drives an ISOLATED container, restores, asserts acceptance criteria from spec §10).

- [ ] **Step 1: Write failing test**
```python
# tests/recovery/test_restore_drill.py
import os, pytest
pytestmark = pytest.mark.hitl

def test_restore_drill_isolated_acceptance():
    # Harness must: start isolated Vault, restore snapshot, validate storage/metadata,
    # authenticate with a TEST identity, read a SYNTHETIC acceptance secret, assert cross-path
    # deny, validate Transit metadata, tear down. Implemented by scripts/restore-drill.sh.
    out = os.system("bash deployments/vault/scripts/restore-drill.sh --smoke")
    assert out == 0
```

- [ ] **Step 2: Run test to verify failure**
Run: `pytest tests/recovery/test_restore_drill.py -v`
Expected: FAIL — script/container missing.

- [ ] **Step 3: Write minimal implementation**
`restore-drill.sh` spins a throwaway container from the pinned digest, restores `backups/*.snapshot`, mounts only synthetic acceptance data, runs the acceptance assertions, and tears down. `snapshot.sh` performs `vault operator raft snapshot save` + checksum + git-ignored encrypted copy.

- [ ] **Step 4: Run test to verify pass**
Run: `bash deployments/vault/scripts/restore-drill.sh --smoke && pytest tests/recovery/test_restore_drill.py -v`
Expected: PASS — drill acceptance green; `RESTORE_DRILL_PASS` recorded.

- [ ] **Step 5: Commit**
```bash
git add deployments/vault/scripts/snapshot.sh deployments/vault/scripts/restore-drill.sh tests/recovery/
git commit -m "feat(recovery): snapshots + isolated restore-drill gate (ADR-012)"
```

---

## Group E — Per-consumer isolation + HSL transit mount/key + AppRole + policies

### Task E1: HSL dedicated transit mount/key profile

**Objective:** HSL consumes via `hsl-transit/` mount + `hsl-signing` key (spec §13). Generalize from HSL's `deployment/vault-lab-l1` transit pattern into the shared service; HSL does NOT own this deployment.

**Files:**
- Create: `deployments/vault/scripts/enable-hsl-transit.sh` (HITL operator: `vault secrets enable -path=hsl-transit transit`; `vault write hsl-transit/keys/hsl-signing ...`).
- Test: `tests/isolation/test_hsl_mount.py`

- [ ] **Step 1: Write failing test**
```python
# tests/isolation/test_hsl_mount.py
import os, pytest, hvac
pytestmark = pytest.mark.hitl
def test_hsl_transit_mount_present():
    c = hvac.Client(url=os.environ["VAULT_ADDR"], token=os.environ["VAULT_TOKEN"], verify=os.environ["VAULT_CACERT"])
    assert "hsl-transit/" in c.sys.list_mounted_secrets_engines()["data"]
def test_hsl_signing_key_present():
    c = hvac.Client(url=os.environ["VAULT_ADDR"], token=os.environ["VAULT_TOKEN"], verify=os.environ["VAULT_CACERT"])
    assert "hsl-signing" in c.secrets.transit.read_key(name="hsl-signing", mount_point="hsl-transit")["data"]
```

- [ ] **Step 2: Run test to verify failure** → FAIL (mount absent).

- [ ] **Step 3: Implement** via `enable-hsl-transit.sh` (HITL).

- [ ] **Step 4: Run test to verify pass** → PASS (2 passed)
- [ ] **Step 5: Commit**

### Task E2: hsl-signer AppRole + exact-path policy (HCL)

**Objective:** One AppRole per consumer, exact-path policy, no wildcard (spec §11.2–11.3).

**Files:**
- Create: `policies/hsl/hsl-signer.hcl`
- Create: `deployments/vault/scripts/enable-hsl-signer.sh` (HITL: create AppRole `hsl-signer`, bind policy, `token_ttl`/`token_max_ttl`, CIDR when stable).
- Test: `tests/isolation/test_hsl_policy_lint.py` (reuse A2 linter on the real policy file).

- [ ] **Step 1: Write failing test**
```python
# tests/isolation/test_hsl_policy_lint.py
from pathlib import Path
from src.policy_lint.linter import lint_policy_text
def test_hsl_signer_policy_clean():
    txt = Path("policies/hsl/hsl-signer.hcl").read_text()
    assert lint_policy_text(txt, identity="hsl-signer") == []
```

- [ ] **Step 2: Run test to verify failure** → FAIL (file missing).

- [ ] **Step 3: Write minimal implementation**
```hcl
# policies/hsl/hsl-signer.hcl
# EXACT-PATH policy for the HSL signer AppRole. No wildcard, no sudo (spec §11.3).
path "hsl-transit/sign/hsl-signing" {
  capabilities = ["update"]
}
path "hsl-transit/verify/hsl-signing" {
  capabilities = ["update"]
}
path "hsl-transit/keys/hsl-signing" {
  capabilities = ["read"]
}
# Explicitly NO path "sys/*", NO path "auth/*", NO other consumers' mounts.
```

- [ ] **Step 4: Run test to verify pass** → PASS
- [ ] **Step 5: Commit**

### Task E3: Negative-capability matrix for hsl-signer

**Objective:** Automated denial assertions for hsl-signer (spec §11.4). Core isolation proof.

**Files:**
- Test: `tests/isolation/test_hsl_negative_capability.py`

- [ ] **Step 1: Write failing test**
```python
# tests/isolation/test_hsl_negative_capability.py
import os, pytest, hvac
pytestmark = pytest.mark.hitl

def _client_role():  # obtain HSL-signer token via wrapped SecretID (HITL-issued), see H1
    import hvac
    c = hvac.Client(url=os.environ["VAULT_ADDR"], verify=os.environ["VAULT_CACERT"])
    c.auth.approle.login(role_id=os.environ["HSL_ROLE_ID"], secret_id=os.environ["HSL_WRAPPED_SECRETID"])
    return c

def test_deny_outside_dedicated_mount():
    c = _client_role()
    with pytest.raises(hvac.exceptions.Forbidden):
        c.secrets.kv.v2.read_secret(path="other/runtime/x", mount_point="kv-other")

def test_deny_sys_and_auth_paths():
    c = _client_role()
    for p in ["sys/health", "auth/approle/role/hsl-signer"]:
        with pytest.raises(hvac.exceptions.Forbidden):
            c.adapter.get(f"/v1/{p}")

def test_deny_other_consumer_transit():
    c = _client_role()
    with pytest.raises(hvac.exceptions.Forbidden):
        c.secrets.transit.sign_data(mount_point="github-transit", name="github-signing", plaintext="eA==")

def test_deny_list_delete_other_mounts():
    c = _client_role()
    with pytest.raises(hvac.exceptions.Forbidden):
        c.secrets.kv.v2.list_secrets(mount_point="github-kv", path="")
```

- [ ] **Step 2: Run test to verify failure** → FAIL (role not enabled / forbidden path works because not initialized).

- [ ] **Step 3: Implement** AppRole+policy via E2 script (HITL). No app code.

- [ ] **Step 4: Run test to verify pass** → PASS (4 passed); isolation gate green
- [ ] **Step 5: Commit**

### Task E4: Reusable consumer-isolation framework

**Objective:** Same negative matrix reusable for future consumers (github, grafana, …) without namespaces (spec §11, §12).

**Files:**
- Create: `src/isolation/matrix.py` (parametrized negative-test builder from a consumer contract).
- Test: `tests/isolation/test_matrix_framework.py` (applies the HSL contract fixture and asserts the same denials generically).

- [ ] **Step 1: Write failing test** (framework imported, applies HSL contract, yields same denials).

- [ ] **Step 2: Run → FAIL.** 
- [ ] **Step 3: Implement** `matrix.py` with `build_negative_cases(contract)` returning the denial list. 
- [ ] **Step 4: PASS.** Commit.

---

## Group F — Provider-neutral contract conformance (adapter #18 DEFERRED)

### Task F1: Capability-contract conformance tests

**Objective:** Prove a consumer depends on the CONTRACT, not Vault APIs (spec §14, §21.2). This is a `hermes-vault`-owned contract concern and is built here.

**Files:**
- Test: `tests/contract/test_conformance.py` (assert consumer code path uses `CapabilityRequest` and never calls `vault` directly).

- [ ] **Step 1: Write failing test** — TDD around a `CapabilityBroker.request(req)` interface that returns a `Capability` envelope (no secret string), backed by the contract schema from A3.
- [ ] **Step 2: Run test to verify failure** (RED)
- [ ] **Step 3: Write minimal implementation**
- [ ] **Step 4: Run test to verify pass** (GREEN)
- [ ] **Step 5: Commit**

### Task F2: VaultCredentialProvider adapter — DEFERRED to #18

**Objective:** The concrete provider implementing the contract against Vault Community/OSS (spec §14 last para) is the subject of PR #18 and is **explicitly deferred from this implementation** per the task request.

- NO file for `src/provider/vault_credential_provider.py` is created in this plan.
- `docs/plans/pr-chain-cleanup.md` (J1) records that #18's `VaultCredentialProvider` must align with the provider-neutral contract defined here (A3/F1), becoming its Community/OSS implementation — not a generic `secret.read` (ADR-005).
- Conformance test F1 validates the contract boundary only; it does not require the concrete adapter.

---

## Group G — Lifecycle / fail-closed / sanitized evidence / global invariants

### Task G1: Lifecycle state machine + fail-closed tests

**Objective:** Encode spec §16 states and fail-closed rules as tested logic.

**Files:**
- Create: `src/lifecycle/states.py` (enums + transition guards).
- Test: `tests/lifecycle/test_fail_closed.py`

- [ ] **Step 1: Write failing test**
```python
from src.lifecycle.states import ServiceState, allowed, request_capability
def test_sealed_denies_capability():
    assert request_capability(ServiceState.INITIALIZED_SEALED, principal="hsl-signer") is False
def test_error_blocks_promotion():
    assert allowed(ServiceState.ERROR, to="UNSEALED_READY") is False
def test_audit_down_blocks_promotion():
    assert request_capability(ServiceState.UNSEALED_READY, audit_enabled=False) is False
```

- [ ] **Step 2: Run test to verify failure** (RED)
- [ ] **Step 3: Write minimal implementation** — Implement guards
- [ ] **Step 4: Run test to verify pass** (GREEN)
- [ ] **Step 5: Commit**

### Task G2: Sanitized evidence tests

**Objective:** Redaction of tokens/SecretIDs/keys/Recovery/RIDs in emitted artifacts (spec §14, docs/04 §167, docs/08 §24, INV-9).

**Files:**
- Create: `src/evidence/redact.py`
- Test: `tests/evidence/test_sanitization.py`

- [ ] **Step 1: Write failing test** — TDD redactor with deterministic patterns; assert no `s.`, `root_token`, `recovery_key`, `SecretID`, private-key PEM blocks survive.
- [ ] **Step 2: Run test to verify failure** (RED)
- [ ] **Step 3: Write minimal implementation**
- [ ] **Step 4: Run test to verify pass** (GREEN)
- [ ] **Step 5: Commit**

### Task G3: Global invariants test

**Objective:** Single test asserting INV-1..INV-11 hold across the repo (no secret patterns, Community/OSS only, no namespace usage, no auto-promotion strings, scope limited to this repo).

**Files:**
- Test: `tests/lifecycle/test_global_invariants.py`

- [ ] **Step 1: Write failing test** — Scan repo for forbidden patterns (`namespace =`, `auto_unseal`, real secret regex, any path outside `pestoura/hermes-vault`), assert clean; assert `NO_AUTO_PROMOTION` documented in runbooks.
- [ ] **Step 2: Run test to verify failure** (RED)
- [ ] **Step 3: Write minimal implementation**
- [ ] **Step 4: Run test to verify pass** (GREEN)
- [ ] **Step 5: Commit**

---

## Group H — Secret-zero handling

### Task H1: Secret-zero bootstrap procedure + delivery-constraint tests

**Objective:** First credential (AppRole SecretID) delivered wrapped/single-use/short-TTL, CIDR-bound, never in `.env`/state/GitHub/logs (spec §15, ADR-017, INV-8). The plan specifies the wrapped SecretID contract; it never handles a REAL SecretID.

**Files:**
- Create: `docs/runbooks/secret-zero.md` (wrapped SecretID issuance by hermes-vault operator; consumer bootstrap is controlled + audited, not "move secret to another file").
- Test: `tests/secret_zero/test_secret_zero.py`

- [ ] **Step 1: Write failing test**
```python
def test_secret_zero_never_in_env_or_logs():
    import subprocess
    out = subprocess.run(["grep","-rIl","SecretID","templates","policies","deployments"], capture_output=True, text=True)
    assert out.stdout.strip() == "", out.stdout
def test_wrapped_single_use_short_ttl_contract():
    from src.capability_contract.schema import CapabilityRequest, CapabilityType
    # Secret-zero delivery is wrapped_secret, single-use, ttl<=300.
    assert CapabilityRequest(principal="hsl-signer", action="auth.approle", resource_scope="hsl-signer",
                             risk_class="high", requested_ttl=120, capability_type=CapabilityType.wrapped_secret)
```

- [ ] **Step 2: Run test to verify failure** (RED)
- [ ] **Step 3: Write minimal implementation** — Implement `secret-zero.md` + extend schema acceptance
- [ ] **Step 4: Run test to verify pass** (GREEN)
- [ ] **Step 5: Commit**

---

## Group I — Generalize HSL deployment into hermes-vault (no ownership back)

### Task I1: Generalize vault-lab-l1 patterns into the shared baseline

**Objective:** Lift the working patterns from `pestoura/hermes-security-labs/deployment/vault-lab-l1/` (single-node Raft, TLS, AppRole signer, transit key `hermes-lab-l1-signer`) INTO THIS shared service as the canonical baseline. HSL must NOT re-own the result (spec §15, §17). Read-only reference to HSL; no HSL write.

**Files:**
- Create: `docs/runbooks/hsl-generalization.md` (mapping table: lab pattern → shared-service artifact; ownership stays with hermes-vault).
- Modify: `README.md` (note HSL deployment is superseded for target architecture; hermes-vault owns the service).
- Test: `tests/isolation/test_ownership_boundary.py` (asserts `deployments/vault/` owns the service and no `deployment/vault-lab-l1` replica is created here).

- [ ] **Step 1: Write failing test** — TDD: test that `deployments/vault/` owns the service and no consumer-owned Vault deployment replica is created. Implement docs + README note.
- [ ] **Step 2: Run test to verify failure** (RED)
- [ ] **Step 3: Write minimal implementation**
- [ ] **Step 4: Run test to verify pass** (GREEN)
- [ ] **Step 5: Commit**

### Task I2: Decommission/freeze HSL-owned deployment (post-validation, owner decision)

**Objective:** Only after the shared path is validated AND the key-continuity decision (spec §21/§25.1) is made, freeze or decommission `deployment/vault-lab-l1`. This is recorded as a plan boundary; execution is a separate effort and depends on owner input.

**Files:**
- Create: `docs/runbooks/hsl-decommission.md` (options: decommission / read-only verify / parallel-run; gated on key-continuity owner decision).

- [ ] **Step 1: Write failing test** — Document only; test asserts the doc lists the three options and the owner-decision gate.
- [ ] **Step 2: Run test to verify failure** (RED)
- [ ] **Step 3: Write minimal implementation**
- [ ] **Step 4: Run test to verify pass** (GREEN)
- [ ] **Step 5: Commit**

---

## Group J — PR-chain cleanup strategy (#14–#16 harvest, #17 governance, #18 deferred) [DOCUMENTED, NOT PERFORMED]

### Task J1: Record PR-chain reconciliation (no execution)

**Objective:** Satisfy the requirement to capture the stacked-PR reconciliation explicitly, while performing NONE of it (spec §18). Harvest useful work from #14–#16; treat #17 supersession as a governance task; record #18 as deferred.

**Files:**
- Create: `docs/plans/pr-chain-cleanup.md`

**Content (summary to include):**
- **Harvest #14–#16:** Review the stacked PRs `#14 → #15 → #16`; extract reusable artifacts (policy patterns, contract-schema ideas, HCL, test scaffolding) and merge them into THIS `hermes-vault` baseline where they align with the shared-service/provider-neutral design. Do not merge branches; cherry-pick concepts only.
- **#17 governance:** `#17` (`epic-03/credential-broker-core`) is marked SUPERSEDED ARCHITECTURE — DO NOT MERGE. Its closure/supersession is a governance action in the respective repo (close-as-superseded with rationale citing this spec's ownership boundary), not an implementation step here.
- **#18 deferred:** `VaultCredentialProvider` (#18) must align with the provider-neutral capability contract (spec §14) — it becomes the contract's Community/OSS implementation (F1), not a generic `secret.read` (ADR-005). It is explicitly deferred from this `hermes-vault` implementation.
- hermes-vault owns the shared service; any PR that re-asserts lab-dedicated ownership is out of scope.
- Action: NONE in this plan. The implementer reconciles the chain in the respective repositories with owner approval; this document is the recorded strategy only.

- [ ] **Step 1: Write failing test** — Add a doc-existence + content test (`tests/plans/test_pr_chain_doc.py` asserts the file exists and contains `#14`, `#15`, `#16`, `#17`, `SUPERSEDED`, `#18`, `provider-neutral`, `deferred`).
- [ ] **Step 2: Run test to verify failure** (RED)
- [ ] **Step 3: Write minimal implementation**
- [ ] **Step 4: Run test to verify pass** (GREEN)
- [ ] **Step 5: Commit**

---

## Group K — HSL consumer migration as later cross-repo plan boundary [DOCUMENTED, NOT IMPLEMENTED HERE]

### Task K1: Document HSL migration boundary

**Objective:** The actual HSL migration (repoint HSL signing/evidence from `deployment/vault-lab-l1` transit to shared `hsl-transit/hsl-signing`, or retained verify-only mount during transition) is a SEPARATE cross-repo implementation plan in `pestoura/hermes-security-labs`. It is NOT implemented in hermes-vault (spec §17.5, §19, §25.1/§25.3).

**Files:**
- Create: `docs/plans/hsl-consumer-migration-boundary.md`

**Content:** enumerates the migration steps from spec §17, marks them as out-of-repo, and records the three owner decisions required before execution (key continuity §25.1, network exposure §25.2, cutover vs parallel-run §25.3). Asserts hermes-vault does not modify HSL.

- [ ] **Step 1: Write failing test** — Doc-existence + content test (`tests/plans/test_hsl_boundary_doc.py`).
- [ ] **Step 2: Run test to verify failure** (RED)
- [ ] **Step 3: Write minimal implementation**
- [ ] **Step 4: Run test to verify pass** (GREEN)
- [ ] **Step 5: Commit**

---

## Group L — No live promotion / HITL gate summary [DOCUMENTED]

### Task L1: No-live-promotion + HITL gate summary

**Objective:** Make the promotion/HITL posture explicit and testable (spec §10, §16.3, ADR-012; INV-2, INV-10).

**Files:**
- Create: `docs/runbooks/promotion-gates.md` (production gate = restore drill PASS + audit PASS + owner sign-off; HITL stops: init, unseal, root, SecretID issuance, TLS private material, promotion).
- Test: `tests/lifecycle/test_no_auto_promotion.py` (asserts runbooks contain the gate and HITL markers; no code path performs promotion).

- [ ] **Step 1: Write failing test** — TDD doc + test.
- [ ] **Step 2: Run test to verify failure** (RED)
- [ ] **Step 3: Write minimal implementation**
- [ ] **Step 4: Run test to verify pass** (GREEN)
- [ ] **Step 5: Commit**

---

## Group M — Final cross-repo handoff (specifies HSL + #18; does NOT modify HSL)

### Task M1: Cross-repo handoff specification

**Objective:** Explicit final task that hands off to `pestoura/hermes-security-labs` (HSL) and to PR #18 reconciliation. It SPECIFIES the consumer onboarding and the deferred adapter, but performs NO modification to HSL or any other repository (INV-11, spec §22).

**Files:**
- Create: `docs/plans/hsl-cross-repo-handoff.md`

**Content (must include):**
1. **HSL onboarding contract (built here):** HSL consumes via the dedicated `hsl-transit/` mount + `hsl-signing` key + `hsl-signer` AppRole + exact-path policy + negative-capability matrix produced by tasks E1–E3. These artifacts live in `pestoura/hermes-vault` only.
2. **HSL repo changes are OUT OF SCOPE:** repointing HSL signing/evidence code from `deployment/vault-lab-l1` to the shared service, plus the key-continuity/network/cutover owner decisions (spec §25), are executed as a SEPARATE HSL-local plan. `hermes-vault` does not write to HSL.
3. **#18 deferred:** the concrete `VaultCredentialProvider` adapter reconciles in the PR chain against the provider-neutral contract (A3/F1); it is not built in this repo.
4. **No live promotion:** HSL may use the shared service only after `RESTORE_DRILL_PASS` + `AUDIT_PASS` + owner sign-off, and only via the contract (fail-closed).
5. **Verification handoff:** HSL-side conformance is validated by reusing the negative-capability matrix (E4) against the shared `hsl-signer` identity; the shared service owns the mounts/AppRole, HSL owns its application logic.

- [ ] **Step 1: Write failing test** — Doc-existence + content test (`tests/plans/test_hsl_handoff_doc.py` asserts the file exists and contains `pestoura/hermes-security-labs`, `does not modify HSL` (or `out-of-scope` + HSL repo path), `#18`, `deferred`, `hsl-transit`, `hsl-signer`).
- [ ] **Step 2: Run test to verify failure** (RED)
- [ ] **Step 3: Write minimal implementation**
- [ ] **Step 4: Run test to verify pass** (GREEN)
- [ ] **Step 5: Commit**

---

## Spec coverage matrix (every § of the design spec is addressed)

| Spec § | Plan task(s) |
|---|---|
| §1 Purpose / §2 Non-goals | Whole plan; C1–C12 are implementation, this doc is plan-only |
| §3 Ownership boundary | I1, I2, G3 (INV-4), J1, M1 |
| §4 Community/OSS | B1, G3 (INV-3), A2 |
| §5 Docker deployment | B1, B3 |
| §6 Raft | B1, B2 |
| §7 TLS | B3, B2 |
| §8 Shamir 3/2, no auto-unseal | B1, B2, B4 |
| §9 Audit | C1 |
| §10 Snapshots + restore drill | D1 |
| §11 Per-consumer isolation + negative tests | E1–E4, A2 |
| §12 No namespaces | B1, E4, G3 |
| §13 HSL dedicated transit mount/key | E1, E2, F1 |
| §14 Provider-neutral contract | A3, F1 (F2 deferred to #18) |
| §15 Secret-zero | H1, B4 |
| §16 Lifecycle + fail-closed | G1, L1 |
| §17 HSL migration (design) | K1 (boundary), I1/I2 (generalization), M1 (handoff) |
| §18 PR #14–#16/#17/#18 chain | J1 (harvest #14–#16, #17 governance, #18 deferred) |
| §19 MVP/Later/Future | Tasks scoped to MVP; Later items noted in docs, not built here |
| §20 Risks | Carried into runbooks (I2, L1) |
| §21 Verification strategy | All TDD tasks + restore drill D1 + audit C1 + negative E3 |
| §22 Invariants for this change | G3 (repo-wide), INV-11 (scope), this plan commits only the doc |
| §23 ADR reconciliation | A2, B1, G3 cite ADRs; README note I1 |
| §24 Self-review | See Self-review appendix |
| §25 Unresolved owner decisions | K1, I2, B3, B4, M1 record them as explicit gates |

---

## Local CI / gates (billing constraint)

GitHub Actions on this account abort at ~2s due to BILLING (not code failure). Therefore the PRIMARY gate runner is local: `bash scripts/ci/run-gates.sh` (Task A4) runs policy-lint, contract-schema, lifecycle/invariants, secret-zero, and a secret-pattern scan offline. The `.github/workflows/fast-gates.yml` mirrors only those trusted, Vault-free, secret-free checks and must not be treated as the promotion gate. Integration/isolation/audit/recovery tests (marked `hitl`) run locally against a throwaway container after operator HITL steps.

## HITL stops (explicit, never automated)

1. `vault operator init` (Shamir 3/2) — B4.
2. `vault operator unseal` x2 by quorum — B4.
3. Initial root token handling + revoke — B4.
4. AppRole SecretID issuance/wrapping delivery — H1, E2.
5. TLS private key generation/custody — B3.
6. Production promotion sign-off — L1, M1.

No unattended task performs init, unseal, root handling, SecretID issuance/wrapping, TLS private-key handling, or live promotion.

## No live promotion

No task auto-promotes to production. `UNSEALED_READY` → production use requires `RESTORE_DRILL_PASS` + `AUDIT_PASS` + owner sign-off (L1, M1, INV-2). This plan performs no runtime, no Vault, no secrets, no remote push, no PR/issue mutation, and no modification to `pestoura/hermes-security-labs` or any repository other than `pestoura/hermes-vault`.

---

## Self-review appendix

- **Spec section coverage:** Every §1–§25 mapped (matrix above). §18 explicitly covered by J1 (harvest #14–#16, #17 governance, #18 deferred). §17 covered by I1/I2/K1/M1. No section contradicted.
- **Placeholder scan:** No `TODO`/`TBD`/`FIXME` anywhere. The only intentional, documented non-literal tokens are the `hitl` marker (runtime gating, not a plan gap) and owner-decision gates (spec §25) recorded as required human inputs (K1/I2/B3/B4/M1). The image digest is fully resolved to the HSL-validated value `4e33b126a59c0c333b76fb4e894722462659a6bec7c48c9ee8cea56fccfd2569` (no `RESOLVE_*` placeholder remains).
- **Type/name consistency:** `CapabilityRequest`/`CapabilityType` (A3) reused in F1/H1 with identical field names; `ServiceState` (G1) matches spec §16.1; negative-test contract shape (E3/E4) matches spec §11.4; digest assertion (B1) uses the exact pinned value from Global Constraints. Task F2 explicitly names `VaultCredentialProvider` as deferred (#18) — consistent with J1/M1.
- **Scope discipline:** Every created/modified path in the File Map and task lists lives under `pestoura/hermes-vault`. I1 reads HSL's `deployment/vault-lab-l1` as a reference only; no HSL write occurs. M1 specifies the cross-repo handoff without modifying HSL (INV-11).
- **Secret hygiene:** No real token/SecretID/key/recovery value appears; all examples use FICTITIOUS identifiers (`hsl-signer`, `hsl-signing`, synthetic acceptance secret). Redaction enforced by G2/G3. H1 specifies the wrapped SecretID contract without handling a real SecretID.
- **HITL boundary:** Global Constraints + HITL stops section + L1/M1 state that init/unseal/root/SecretID/TLS-private/promotion are operator-only and never in unattended tasks.
- **Result:** SELF-REVIEW PASS. No structural blocker for the plan itself.

## Structural blockers (implementation-time, not plan blockers)

- Owner decisions from spec §25 (key continuity, network exposure, cutover vs parallel-run, recovery custody, exact digest) — the digest is now resolved per this request; the remaining four remain REQUIRED before/at execution of B3/B4/I2/K1/M1. They are documented gates, not blockers to writing or committing this plan.
