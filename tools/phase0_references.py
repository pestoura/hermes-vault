from __future__ import annotations

import re
from pathlib import Path
from typing import Sequence

_SECRET_NAME_HINT = re.compile(r"(?i)(?:password|passwd|pwd|token|secret|api[_-]?key|access[_-]?key|client[_-]?secret|credential|auth[_-]?key|signing[_-]?key|private[_-]?key|unseal|recovery|cert|certificate|tls[_-]?key)")
_ENV_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_COMPOSE_SUBSTITUTION = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)[^}]*\}")
_SYSTEMD_ENVFILE = re.compile(r"(?m)^\s*EnvironmentFile\s*=\s*-?([^\s#]+)")
_SYSTEMD_ENV = re.compile(r"(?m)^\s*Environment\s*=\s*(.+)$")
_MAX_REFERENCE_FILE_BYTES = 1_048_576


def classify_reference(name: str, source: str) -> str:
    upper = name.upper()
    if any(marker in upper for marker in ("UNSEAL", "RECOVERY", "ROOT_TOKEN", "BOOTSTRAP")):
        return "bootstrap"
    if any(marker in upper for marker in ("TRANSIT", "SIGNING", "HMAC", "EVIDENCE_SIGN")):
        return "transit"
    if any(marker in upper for marker in ("CERT", "CERTIFICATE", "TLS_KEY", "PRIVATE_KEY", "CA_KEY")):
        return "pki"
    if source in {"env", "compose", "systemd"}:
        return "static"
    return "unknown"


def _provider_hint(name: str) -> str:
    upper = name.upper()
    providers = (
        ("GITHUB", "github"), ("GRAFANA", "grafana"), ("CLOUDFLARE", "cloudflare"),
        ("GOOGLE", "google"), ("GMAIL", "google"), ("MICROSOFT", "microsoft"),
        ("OUTLOOK", "microsoft"), ("PLANNER", "microsoft"), ("HOME_ASSISTANT", "home-assistant"),
        ("TELEGRAM", "telegram"), ("WHATSAPP", "whatsapp"), ("VAULT", "vault"), ("HERMES", "hermes"),
    )
    for marker, provider in providers:
        if marker in upper:
            return provider
    return "unknown"


def _read_reference_file(path: Path) -> str | None:
    try:
        if not path.is_file() or path.stat().st_size > _MAX_REFERENCE_FILE_BYTES:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _secret_names_from_env(text: str) -> set[str]:
    names: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        if key.startswith("export "):
            key = key[7:].strip()
        if _ENV_KEY.match(key) and _SECRET_NAME_HINT.search(key):
            names.add(key)
    return names


def _secret_names_from_compose(text: str) -> set[str]:
    names = {name for name in _COMPOSE_SUBSTITUTION.findall(text) if _SECRET_NAME_HINT.search(name)}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key = line.split(":", 1)[0].strip().strip('"\'')
        if _ENV_KEY.match(key) and _SECRET_NAME_HINT.search(key):
            names.add(key)
    return names


def _secret_names_from_systemd(text: str) -> set[str]:
    names: set[str] = set()
    for match in _SYSTEMD_ENV.finditer(text):
        payload = match.group(1).strip()
        for token in re.findall(r"(?:^|\s|\")([A-Za-z_][A-Za-z0-9_]*)=", payload):
            if _SECRET_NAME_HINT.search(token):
                names.add(token)
    return names


def _reference_source_type(path: Path) -> str:
    name = path.name.lower()
    if name.endswith((".service", ".timer", ".socket", ".target")):
        return "systemd"
    if name in {"compose.yaml", "compose.yml", "docker-compose.yaml", "docker-compose.yml"}:
        return "compose"
    if name.endswith((".yaml", ".yml")) and "compose" in name:
        return "compose"
    return "env"


def collect_secret_references(paths: Sequence[Path]) -> list[dict]:
    references: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for raw_path in paths:
        path = Path(raw_path)
        text = _read_reference_file(path)
        if text is None:
            continue
        source_type = _reference_source_type(path)
        if source_type == "systemd":
            names = _secret_names_from_systemd(text)
            envfiles = [m.group(1) for m in _SYSTEMD_ENVFILE.finditer(text)]
        elif source_type == "compose":
            names = _secret_names_from_compose(text)
            envfiles = []
        else:
            names = _secret_names_from_env(text)
            envfiles = []

        for name in sorted(names):
            key = (name, str(path), source_type)
            if key in seen:
                continue
            seen.add(key)
            references.append({
                "name": name,
                "source_type": source_type,
                "source_path": str(path),
                "consumer_hint": path.stem,
                "provider_hint": _provider_hint(name),
                "classification": classify_reference(name, source_type),
                "accessible": True,
            })
        for envfile in envfiles:
            references.append({
                "name": "ENVIRONMENT_FILE_REFERENCE",
                "source_type": "systemd",
                "source_path": str(path),
                "consumer_hint": path.stem,
                "provider_hint": "unknown",
                "classification": "unknown",
                "accessible": True,
                "reference_path": envfile,
            })
    return references
