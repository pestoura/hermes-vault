from __future__ import annotations

import getpass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from tools.phase0_core import run_command

SYSTEM_UNITS = (
    "docker.service",
    "containerd.service",
    "systemd-timesyncd.service",
    "cron.service",
    "ssh.service",
)
USER_UNITS = (
    "hermes-gateway.service",
    "hermes-dashboard.service",
    "alloy.service",
    "cloudflared-hermes-mcp.service",
    "webhook-hex0r-tunnel.service",
    "spms-mailbox-watcher.service",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_key_values(path: Path, allowed: set[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    try:
        for raw in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key not in allowed:
                continue
            result[key] = value.strip().strip('"').strip("'")
    except (OSError, UnicodeError):
        pass
    return result


def _read_meminfo(path: Path) -> dict[str, int]:
    allowed = {"MemTotal", "MemAvailable"}
    result: dict[str, int] = {}
    try:
        for raw in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
            if ":" not in raw:
                continue
            key, value = raw.split(":", 1)
            key = key.strip()
            if key not in allowed:
                continue
            fields = value.strip().split()
            if not fields:
                continue
            try:
                result[key] = int(fields[0])
            except ValueError:
                continue
    except (OSError, UnicodeError):
        pass
    return result


def collect_host(*, runner=run_command, os_release_path: Path = Path("/etc/os-release"), meminfo_path: Path = Path("/proc/meminfo")) -> dict:
    observed_at = _utc_now()
    uname = runner(["/usr/bin/uname", "-srmo"])
    cpu = runner(["/usr/bin/getconf", "_NPROCESSORS_ONLN"])
    os_release = _read_key_values(Path(os_release_path), {"ID", "VERSION_ID", "PRETTY_NAME"})
    mem = _read_meminfo(Path(meminfo_path))
    try:
        cpu_count = int(cpu.stdout.strip()) if cpu.status == "ok" else None
    except ValueError:
        cpu_count = None
    available = uname.status == "ok" and bool(os_release)
    return {
        "available": available,
        "status": "ok" if available else "inconclusive",
        "observed_at": observed_at,
        "kernel": uname.stdout.strip() if uname.status == "ok" else None,
        "os": {"id": os_release.get("ID"), "version_id": os_release.get("VERSION_ID"), "pretty_name": os_release.get("PRETTY_NAME")},
        "cpu_count": cpu_count,
        "memory": {"total_kib": mem.get("MemTotal"), "available_kib": mem.get("MemAvailable")},
    }


def collect_storage(*, runner=run_command, paths: Sequence[str] = ("/", "/var")) -> dict:
    observed_at = _utc_now()
    obs = runner(["/usr/bin/df", "-P", "-B1", *paths])
    filesystems: list[dict] = []
    if obs.status == "ok":
        lines = [line for line in obs.stdout.splitlines() if line.strip()]
        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 6:
                continue
            filesystem, blocks, used, available, capacity = parts[:5]
            mount = " ".join(parts[5:])
            try:
                filesystems.append({"filesystem": filesystem, "bytes_total": int(blocks), "bytes_used": int(used), "bytes_available": int(available), "capacity": capacity, "mount": mount})
            except ValueError:
                continue
    return {"available": obs.status == "ok", "status": "ok" if obs.status == "ok" and filesystems else "inconclusive", "observed_at": observed_at, "filesystems": filesystems, "reason": None if obs.status == "ok" else obs.status}


def _parse_properties(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def _systemd_argv(unit: str, *, user: bool, hermes_user: str, current_user: str) -> list[str]:
    argv = ["/usr/bin/systemctl"]
    if user:
        argv.append("--user")
        if current_user != hermes_user:
            argv.append(f"--machine={hermes_user}@.host")
    argv.extend(["show", unit, "--no-pager", "--property=LoadState", "--property=ActiveState", "--property=SubState", "--property=UnitFileState"])
    return argv


def collect_systemd(*, runner=run_command, system_units: Sequence[str] = SYSTEM_UNITS, user_units: Sequence[str] = USER_UNITS, hermes_user: str = "estourpm", current_user: str | None = None) -> dict:
    current_user = current_user or getpass.getuser()
    observed_at = _utc_now()
    units: list[dict] = []
    for unit, is_user in [(u, False) for u in system_units] + [(u, True) for u in user_units]:
        obs = runner(_systemd_argv(unit, user=is_user, hermes_user=hermes_user, current_user=current_user))
        props = _parse_properties(obs.stdout) if obs.status == "ok" else {}
        units.append({
            "name": unit,
            "scope": "user" if is_user else "system",
            "owner": hermes_user if is_user else "root/system",
            "status": "ok" if obs.status == "ok" else "inconclusive",
            "reason": None if obs.status == "ok" else obs.status,
            "load_state": props.get("LoadState"),
            "active_state": props.get("ActiveState"),
            "sub_state": props.get("SubState"),
            "unit_file_state": props.get("UnitFileState"),
        })
    available = any(unit["status"] == "ok" for unit in units)
    return {"available": available, "status": "ok" if available else "inconclusive", "observed_at": observed_at, "units": units}


def collect_docker(*, runner=run_command) -> dict:
    observed_at = _utc_now()
    version = runner(["/usr/bin/docker", "version", "--format", "{{.Server.Version}}"])
    ps = runner(["/usr/bin/docker", "ps", "--format", "{{.Names}}\\t{{.Image}}\\t{{.Status}}"])
    containers: list[dict] = []
    if ps.status == "ok":
        for line in ps.stdout.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) == 3:
                containers.append({"name": parts[0], "image": parts[1], "status": parts[2]})
    available = version.status == "ok"
    return {"available": available, "status": "ok" if available else "inconclusive", "observed_at": observed_at, "server_version": version.stdout.strip() if version.status == "ok" else None, "containers": containers, "reason": None if available else version.status}


def collect_listeners(*, runner=run_command) -> dict:
    observed_at = _utc_now()
    obs = runner(["/usr/sbin/ss", "-H", "-ltn"])
    listeners: list[dict] = []
    if obs.status == "ok":
        for line in obs.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 5:
                listeners.append({"protocol": "tcp", "local": parts[3]})
    return {"available": obs.status == "ok", "status": "ok" if obs.status == "ok" else "inconclusive", "observed_at": observed_at, "listeners": listeners, "reason": None if obs.status == "ok" else obs.status}
