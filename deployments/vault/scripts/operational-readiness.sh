#!/usr/bin/env bash
# Secret-free 24x7 runtime readiness check for the canonical Hermes Vault service.
set -euo pipefail

CONTAINER="${VAULT_CONTAINER_NAME:-vault-vault-1}"
EXPECTED_IMAGE="hashicorp/vault:1.21.4@sha256:4e33b126a59c0c333b76fb4e894722462659a6bec7c48c9ee8cea56fccfd2569"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CA="${VAULT_CACERT:-${DEPLOY_DIR}/certs/ca.pem}"
ADDR="${VAULT_ADDR:-https://127.0.0.1:8200}"

fail() {
  echo "VAULT_24X7_FAIL reason=$1" >&2
  exit 3
}

command -v docker >/dev/null 2>&1 || fail docker_missing
docker info >/dev/null 2>&1 || fail docker_unavailable
[[ -f "${CA}" ]] || fail ca_missing
[[ "${ADDR}" == "https://127.0.0.1:8200" ]] || fail noncanonical_addr

docker inspect "${CONTAINER}" >/dev/null 2>&1 || fail container_missing
RUNNING="$(docker inspect "${CONTAINER}" --format '{{.State.Running}}')"
[[ "${RUNNING}" == "true" ]] || fail container_not_running
RESTART="$(docker inspect "${CONTAINER}" --format '{{.HostConfig.RestartPolicy.Name}}')"
[[ "${RESTART}" == "unless-stopped" ]] || fail "RestartPolicy=${RESTART:-none}"

IMAGE="$(docker inspect "${CONTAINER}" --format '{{.Config.Image}}')"
[[ "${IMAGE}" == "${EXPECTED_IMAGE}" ]] || fail image_mismatch

NETWORKS="$(docker inspect "${CONTAINER}" --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}')"
grep -qw 'hermes-security-plane' <<<"${NETWORKS}" || fail security_plane_missing
grep -qw 'hermes-vault-admin' <<<"${NETWORKS}" || fail admin_network_missing

MOUNTS="$(docker inspect "${CONTAINER}" --format '{{range .Mounts}}{{println .Name .Destination .RW}}{{end}}')"
grep -Eq '^vault_vault-data /vault/file true$' <<<"${MOUNTS}" || fail raft_volume_missing
grep -Eq '^vault_vault-audit /vault/logs true$' <<<"${MOUNTS}" || fail audit_volume_missing

PORTS="$(docker port "${CONTAINER}" 8200/tcp 2>/dev/null || true)"
[[ "${PORTS}" == "127.0.0.1:8200" ]] || fail loopback_port_mismatch

echo "VAULT_24X7_TOPOLOGY_PASS RestartPolicy=${RESTART}"

set +e
HEALTH="$(python3 - "${ADDR}" "${CA}" <<'PY'
import json, ssl, sys, urllib.error, urllib.request
addr, ca = sys.argv[1:]
ctx = ssl.create_default_context(cafile=ca)
req = urllib.request.Request(addr + "/v1/sys/health?standbyok=true&perfstandbyok=true")
try:
    with urllib.request.urlopen(req, context=ctx, timeout=5) as r:
        code, body = r.status, r.read()
except urllib.error.HTTPError as e:
    code, body = e.code, e.read()
try:
    data = json.loads(body.decode("utf-8"))
except Exception:
    print(f"code={code} initialized=unknown sealed=unknown")
    sys.exit(4)
print(f"code={code} initialized={str(data.get('initialized')).lower()} sealed={str(data.get('sealed')).lower()}")
if code == 200 and data.get("initialized") is True and data.get("sealed") is False:
    sys.exit(0)
if data.get("initialized") is True and data.get("sealed") is True:
    sys.exit(2)
sys.exit(4)
PY
)"
RC=$?
set -e

case "${RC}" in
  0)
    echo "${HEALTH}"
    echo "VAULT_24X7_READY"
    ;;
  2)
    echo "${HEALTH}"
    echo "VAULT_24X7_SEALED_NEEDS_QUORUM" >&2
    exit 2
    ;;
  *)
    echo "${HEALTH}" >&2
    fail health_unexpected
    ;;
esac
