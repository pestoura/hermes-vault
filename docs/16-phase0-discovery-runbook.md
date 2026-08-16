# Phase 0 — Jarvas/Hermes discovery runbook

## Purpose

Run Vault Phase 0 discovery on Jarvas without installing Vault, restarting services, mutating Docker/systemd, or exposing secret values. The collector records bounded operational metadata and secret references/names only.

## Safety boundary

- argv subprocesses with `shell=False`;
- command timeout at most 30 seconds;
- bounded, defensively redacted command output;
- systemd reads only `LoadState`, `ActiveState`, `SubState`, `UnitFileState`;
- Docker reads server version plus container name/image/status only;
- secret discovery extracts variable/key names and reference paths, never values;
- certificates use `openssl x509 -noout`; private-key-looking paths are rejected;
- report files are written atomically with mode `0600`.

Never paste `.env` contents, tokens, Shamir shares, private keys, SecretIDs, root tokens, Vault client tokens or raw credential-bearing configuration into issues/chat.

## Preflight

Use an authenticated checkout of `pestoura/hermes-vault` on Jarvas:

```bash
cd /path/to/hermes-vault
git status --short
git rev-parse HEAD
python3 --version
```

Python 3.12+ is intended; the collector has no third-party runtime dependency.

## Read-only discovery

```bash
PYTHONPATH=. python3 tools/phase0_discovery.py --pretty
```

Return code `2` means at least one mandatory observation is missing/inconclusive; it is a gate result, not permission to bypass it.

Canonical evidence file:

```bash
mkdir -p "$HOME/.local/state/hermes-vault"
chmod 700 "$HOME/.local/state/hermes-vault"
PYTHONPATH=. python3 tools/phase0_discovery.py \
  --output "$HOME/.local/state/hermes-vault/phase0-discovery.json"
PYTHONPATH=. python3 tools/validate_phase0.py \
  "$HOME/.local/state/hermes-vault/phase0-discovery.json"
stat -c '%a %n' "$HOME/.local/state/hermes-vault/phase0-discovery.json"
```

Expected mode: `600`.

## Optional public certificate metadata

Pass public certificate files only; never a private-key path:

```bash
PYTHONPATH=. python3 tools/phase0_discovery.py \
  --cert-path /path/to/public/server-certificate.pem \
  --output "$HOME/.local/state/hermes-vault/phase0-discovery.json"
```

## Optional existing Vault CLI observation

If Vault CLI already exists, observe only its version:

```bash
PYTHONPATH=. python3 tools/phase0_discovery.py \
  --vault-binary "$(command -v vault)" \
  --output "$HOME/.local/state/hermes-vault/phase0-discovery.json"
```

Absence of a host Vault CLI is not an install failure because the LAB_L1 target is containerized. Phase 0 never installs, initializes or unseals Vault.

## Additional reference files

```bash
PYTHONPATH=. python3 tools/phase0_discovery.py \
  --reference-path /absolute/path/to/consumer.env \
  --reference-path /absolute/path/to/consumer.service \
  --output "$HOME/.local/state/hermes-vault/phase0-discovery.json"
```

Only explicit/defaulted files are read; emitted fields are names, locations, consumer/provider hints and classification.

## Evidence handling

Allowed in EPIC-00:

- report schema/version;
- collector Git SHA;
- report SHA-256;
- gate statuses;
- sanitized inventory counts;
- missing/inconclusive observation names.

Do not attach raw source files.

```bash
sha256sum "$HOME/.local/state/hermes-vault/phase0-discovery.json"
```

## Cleanup

Only the generated evidence needs cleanup:

```bash
rm -f "$HOME/.local/state/hermes-vault/phase0-discovery.json"
```

Do not alter source `.env`, systemd, Compose, TLS, Hermes or Jarvas files.

## P0 authority boundaries

`DISCOVERY_COMPLETE` is deterministic/fail-closed. These remain separate:

```text
NO_SECRET_IN_REPO             -> repository secret-safety CI/review
TARGET_ARCHITECTURE_APPROVED  -> governance/human decision
RECOVERY_DESIGN_DEFINED       -> recovery-design review
```

Repository GREEN or discovery PASS does not install Vault, initialize/unseal it, bind trust, select a signer, or authorize Runner target effect.
