#!/usr/bin/env python3
"""Daily Hermes Vault Raft snapshot using a dedicated AppRole workload identity."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

CANONICAL_ADDR = "https://127.0.0.1:8200"
LOGIN_PATH = "/v1/auth/approle/login"
SNAPSHOT_PATH = "/v1/sys/storage/raft/snapshot"
REVOKE_PATH = "/v1/auth/token/revoke-self"


def fail(message: str) -> "NoReturn":
    print(f"SCHEDULED_SNAPSHOT_FAIL reason={message}", file=sys.stderr)
    raise SystemExit(3)


def read_credential(name: str) -> str:
    directory = os.environ.get("CREDENTIALS_DIRECTORY", "")
    if not directory:
        fail("credentials_directory_missing")
    path = Path(directory) / name
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        fail(f"credential_{name}_missing")
    if not value or "\n" in value or "\r" in value:
        fail(f"credential_{name}_invalid")
    return value

def request_json(ctx: ssl.SSLContext, addr: str, path: str, *, body: dict, token: str | None = None) -> dict:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if token:
        headers["X-Vault-Token"] = token
    req = urllib.request.Request(
        addr + path,
        data=json.dumps(body, separators=(",", ":")).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            payload = response.read(262145)
            if len(payload) > 262144:
                fail("json_response_too_large")
    except (urllib.error.URLError, TimeoutError, ssl.SSLError):
        fail("vault_request_failed")
    try:
        decoded = json.loads(payload.decode("utf-8")) if payload else {}
    except (UnicodeDecodeError, json.JSONDecodeError):
        fail("vault_response_invalid")
    if not isinstance(decoded, dict):
        fail("vault_response_invalid")
    return decoded


def capture_snapshot(ctx: ssl.SSLContext, addr: str, token: str, target: Path) -> None:
    req = urllib.request.Request(addr + SNAPSHOT_PATH, headers={"X-Vault-Token": token}, method="GET")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=60) as response, target.open("xb") as output:
            os.chmod(target, 0o600)
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
    except Exception:
        target.unlink(missing_ok=True)
        fail("snapshot_capture_failed")

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def encrypt_snapshot(snapshot: Path, encrypted: Path, passphrase_path: Path) -> None:
    tmp = encrypted.with_suffix(encrypted.suffix + ".partial")
    try:
        subprocess.run(
            [
                "openssl", "enc", "-aes-256-cbc", "-salt", "-pbkdf2",
                "-in", str(snapshot), "-out", str(tmp),
                "-pass", f"file:{passphrase_path}",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        os.chmod(tmp, 0o600)
        os.replace(tmp, encrypted)
    except (OSError, subprocess.CalledProcessError):
        tmp.unlink(missing_ok=True)
        fail("snapshot_encryption_failed")


def apply_retention(directory: Path, retention: int) -> None:
    snapshots = sorted(directory.glob("vault-raft-*.snapshot"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in snapshots[retention:]:
        for suffix in ("", ".sha256", ".meta.json", ".enc", ".enc.sha256"):
            Path(str(old) + suffix).unlink(missing_ok=True)

def main() -> int:
    addr = os.environ.get("VAULT_ADDR", CANONICAL_ADDR)
    ca = Path(os.environ.get("VAULT_CACERT", ""))
    role_id = os.environ.get("VAULT_BACKUP_ROLE_ID", "").strip()
    backup_dir = Path(os.environ.get("VAULT_BACKUP_DIR", "")).expanduser()
    try:
        retention = int(os.environ.get("VAULT_SNAPSHOT_RETENTION", "14"))
    except ValueError:
        fail("retention_invalid")
    if addr != CANONICAL_ADDR:
        fail("noncanonical_addr")
    if not ca.is_file():
        fail("ca_missing")
    if not role_id or not backup_dir.is_absolute() or retention < 2 or retention > 90:
        fail("configuration_invalid")

    credentials = Path(os.environ.get("CREDENTIALS_DIRECTORY", ""))
    secret_id = read_credential("backup-secret-id")
    passphrase_path = credentials / "snapshot-passphrase"
    if not passphrase_path.is_file():
        fail("credential_snapshot-passphrase_missing")

    ctx = ssl.create_default_context(cafile=str(ca))
    login = request_json(ctx, addr, LOGIN_PATH, body={"role_id": role_id, "secret_id": secret_id})
    secret_id = ""
    auth = login.get("auth") if isinstance(login.get("auth"), dict) else {}
    client_token = auth.get("client_token")
    policies = auth.get("token_policies") or auth.get("policies") or []
    if not isinstance(client_token, str) or not client_token:
        fail("approle_login_missing_token")
    if set(policies) != {"vault-backup-snapshot"}:
        fail("approle_policy_mismatch")

    os.umask(0o077)
    backup_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(backup_dir, 0o700)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot = backup_dir / f"vault-raft-{stamp}.snapshot"
    encrypted = Path(str(snapshot) + ".enc")

    revoked = False
    try:
        capture_snapshot(ctx, addr, client_token, snapshot)
        snap_sha = sha256_file(snapshot)
        Path(str(snapshot) + ".sha256").write_text(f"{snap_sha}  {snapshot.name}\n", encoding="utf-8")
        os.chmod(Path(str(snapshot) + ".sha256"), 0o600)

        # AES-256-CBC with PBKDF2; passphrase is supplied only as a systemd credential file.
        encrypt_snapshot(snapshot, encrypted, passphrase_path)
        enc_sha = sha256_file(encrypted)
        enc_sum = Path(str(encrypted) + ".sha256")
        enc_sum.write_text(f"{enc_sha}  {encrypted.name}\n", encoding="utf-8")
        os.chmod(enc_sum, 0o600)

        metadata = {
            "artifact": "vault.raft.snapshot",
            "mode": "scheduled-24x7",
            "captured_at_utc": stamp,
            "vault_addr": CANONICAL_ADDR,
            "snapshot_file": snapshot.name,
            "sha256": snap_sha,
            "encrypted_file": encrypted.name,
            "encrypted_sha256": enc_sha,
            "encryption": "AES-256-CBC/PBKDF2/systemd-credential",
        }
        meta_path = Path(str(snapshot) + ".meta.json")
        meta_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(meta_path, 0o600)
        apply_retention(backup_dir, retention)
        success = True
    finally:
        req = urllib.request.Request(
            addr + REVOKE_PATH,
            data=b"{}",
            headers={"X-Vault-Token": client_token, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=10):
                revoked = True
        except Exception:
            revoked = False
        client_token = ""
        if not locals().get("success", False):
            for path in (
                snapshot,
                Path(str(snapshot) + ".sha256"),
                Path(str(snapshot) + ".meta.json"),
                encrypted,
                Path(str(encrypted) + ".sha256"),
            ):
                path.unlink(missing_ok=True)

    if not revoked:
        fail("token_self_revoke_failed")
    print(f"SCHEDULED_SNAPSHOT_PASS captured={stamp} sha256={snap_sha} encrypted_sha256={enc_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
