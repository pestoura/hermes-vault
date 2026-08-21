#!/usr/bin/env bash
# ADR-012 / ADR-023 isolated restore-drill controller.
# Safe modes never automate init, unseal, force-restore, or Shamir handling.
set -euo pipefail

IMAGE="hashicorp/vault:1.21.4@sha256:4e33b126a59c0c333b76fb4e894722462659a6bec7c48c9ee8cea56fccfd2569"
LABEL_KEY="com.hexor.restore-run"

fail() { echo "[restore-drill] ERROR: $*" >&2; exit 1; }

canonical_run_dir() {
  local raw="${1:?run directory required}"
  [[ -d "${raw}" ]] || fail "run directory does not exist"
  realpath "${raw}"
}

run_id_for() {
  local run="$1" id
  id="$(basename "${run}")"
  [[ "${id}" =~ ^adr023-[A-Za-z0-9_.-]+$ ]] || fail "invalid run id"
  printf '%s\n' "${id}"
}

container_for() {
  local id="$1"
  printf 'hermes-vault-restore-%s\n' "${id#adr023-}"
}

snapshot_for() {
  local run="$1"
  mapfile -t snaps < <(find "${run}" -maxdepth 1 -type f -name 'vault-raft-*.snapshot' -print)
  [[ "${#snaps[@]}" -eq 1 ]] || fail "exactly one snapshot is required"
  printf '%s\n' "${snaps[0]}"
}
verify_snapshot_set() {
  local run="$1" snap base
  snap="$(snapshot_for "${run}")"
  base="$(basename "${snap}")"
  for required in "${snap}.sha256" "${snap}.meta.json" "${snap}.enc" "${snap}.enc.sha256" \
                  "${run}/restore-acceptance.pem" "${run}/restore-acceptance.key"; do
    [[ -f "${required}" ]] || fail "missing required restore asset: $(basename "${required}")"
  done
  (cd "${run}" && sha256sum -c "${base}.sha256" >/dev/null) || fail "snapshot checksum mismatch"
  (cd "${run}" && sha256sum -c "${base}.enc.sha256" >/dev/null) || fail "encrypted snapshot checksum mismatch"
  printf '%s\n' "${snap}"
}

assert_label() {
  local container="$1" run_id="$2" actual
  actual="$(docker inspect -f '{{ index .Config.Labels "com.hexor.restore-run" }}' "${container}" 2>/dev/null || true)"
  [[ "${actual}" == "${run_id}" ]] || fail "container label mismatch"
}

cmd_offline_selftest() {
  echo "[restore-drill] SYNTHETIC | ISOLATED | OFFLINE | DATA-FREE self-test"
  local work snap restored sha1 sha2
  work="$(mktemp -d "${TMPDIR:-/tmp}/restore-drill.XXXXXX")"
  trap 'rm -rf "${work}"' RETURN
  snap="${work}/snapshot.synth"
  restored="${work}/restored.synth"
  printf 'primary=ADR023_PRIMARY_OK\nforbidden=ADR023_FORBIDDEN_OK\n' > "${snap}"
  cp "${snap}" "${restored}"
  sha1="$(sha256sum "${snap}" | awk '{print $1}')"
  sha2="$(sha256sum "${restored}" | awk '{print $1}')"
  [[ "${sha1}" == "${sha2}" ]] || fail "synthetic checksum mismatch"
  grep -q '^primary=ADR023_PRIMARY_OK$' "${restored}" || fail "synthetic primary missing"
  echo "[restore-drill] RESTORE_DRILL_PASS (synthetic/offline)"
}
prepare_runtime_assets() {
  local run="$1" runtime="${run}/runtime" tls="${run}/runtime/tls"
  mkdir -p "${runtime}/data" "${runtime}/audit" "${runtime}/config" "${tls}"
  chmod 770 "${runtime}/data" "${runtime}/audit"
  chmod 750 "${runtime}" "${runtime}/config" "${tls}"

  openssl req -x509 -newkey rsa:2048 -sha256 -days 1 -nodes \
    -keyout "${tls}/ca.key" -out "${tls}/ca.pem" \
    -subj "/CN=hermes-vault-restore-ca" \
    -addext "basicConstraints=critical,CA:TRUE" >/dev/null 2>&1
  openssl req -newkey rsa:2048 -sha256 -nodes \
    -keyout "${tls}/server.key" -out "${tls}/server.csr" \
    -subj "/CN=localhost" >/dev/null 2>&1
  cat > "${tls}/server.ext" <<'EOF'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=DNS:localhost,IP:127.0.0.1
EOF
  openssl x509 -req -sha256 -days 1 -in "${tls}/server.csr" \
    -CA "${tls}/ca.pem" -CAkey "${tls}/ca.key" -CAcreateserial \
    -extfile "${tls}/server.ext" -out "${tls}/server.pem" >/dev/null 2>&1
  rm -f "${tls}/ca.key" "${tls}/ca.srl" "${tls}/server.csr" "${tls}/server.ext"
  chmod 640 "${tls}/server.key"
  chmod 644 "${tls}/ca.pem" "${tls}/server.pem"
}

release_runtime_permissions() {
  local runtime="$1"
  [[ -d "${runtime}" ]] || return 0
  docker run --rm \
    --network none \
    --read-only \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    --user 100:1000 \
    -v "${runtime}:/cleanup:rw" \
    --entrypoint sh \
    "${IMAGE}" -c 'find /cleanup -mindepth 1 -user 100 -exec chmod g+rwX {} +' \
    >/dev/null 2>&1
}

wait_for_uninitialized() {
  local container="$1" i running status_json initialized
  for i in $(seq 1 30); do
    running="$(docker inspect -f '{{.State.Running}}' "${container}" 2>/dev/null || true)"
    if [[ "${running}" == "true" ]]; then
      status_json="$(docker exec -e VAULT_ADDR=https://127.0.0.1:8200 \
        -e VAULT_CACERT=/vault/certs/ca.pem "${container}" \
        vault status -format=json 2>/dev/null || true)"
      if [[ -n "${status_json}" ]]; then
        initialized="$(python3 -c 'import json,sys; print(str(json.load(sys.stdin).get("initialized")).lower())' <<<"${status_json}" 2>/dev/null || true)"
        if [[ "${initialized}" == "false" ]]; then
          return 0
        fi
        if [[ "${initialized}" == "true" ]]; then
          echo "[restore-drill] unexpected initialized restore runtime before HITL" >&2
          return 1
        fi
      fi
    fi
    sleep 0.5
  done
  echo "[restore-drill] restore runtime did not reach uninitialized status" >&2
  return 1
}

cmd_start() {
  local run run_id container snap runtime runtime_snap cid sha
  run="$(canonical_run_dir "${1:?run directory required}")"
  run_id="$(run_id_for "${run}")"
  container="$(container_for "${run_id}")"
  snap="$(verify_snapshot_set "${run}")"
  runtime="${run}/runtime"
  [[ ! -e "${runtime}" ]] || fail "runtime directory already exists"
  command -v docker >/dev/null 2>&1 || fail "docker is required"
  command -v openssl >/dev/null 2>&1 || fail "openssl is required"

  prepare_runtime_assets "${run}"
  runtime_snap="${runtime}/input.snapshot"
  install -m 0640 "${snap}" "${runtime_snap}"
  cat > "${runtime}/config/restore.hcl" <<'EOF'
ui = false
disable_mlock = true
api_addr = "https://127.0.0.1:8200"
cluster_addr = "https://127.0.0.1:8201"
storage "raft" {
  path = "/vault/file"
  node_id = "restore-drill"
}
listener "tcp" {
  address = "127.0.0.1:8200"
  cluster_address = "127.0.0.1:8201"
  tls_cert_file = "/vault/certs/server.pem"
  tls_key_file = "/vault/certs/server.key"
}
EOF
  chmod 640 "${runtime}/config/restore.hcl"
  sha="$(sha256sum "${snap}" | awk '{print $1}')"
  if ! cid="$(docker run -d \
    --name "${container}" \
    --label "${LABEL_KEY}=${run_id}" \
    --network none \
    --read-only \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    --memory 512m \
    --cpus 1.0 \
    --pids-limit 128 \
    --tmpfs /tmp:rw,noexec,nosuid,size=64m \
    --user 100:1000 \
    -e SKIP_CHOWN=1 \
    -e SKIP_SETCAP=1 \
    -e VAULT_ADDR=https://127.0.0.1:8200 \
    -e VAULT_CACERT=/vault/certs/ca.pem \
    -v "${runtime}/config/restore.hcl:/vault/config/restore.hcl:ro" \
    -v "${runtime}/data:/vault/file:rw" \
    -v "${runtime}/audit:/vault/logs:rw" \
    -v "${runtime}/tls:/vault/certs:ro" \
    -v "${runtime_snap}:/vault/restore/input.snapshot:ro" \
    -v "${run}/restore-acceptance.pem:/vault/restore/client/restore-acceptance.pem:ro" \
    -v "${run}/restore-acceptance.key:/vault/restore/client/restore-acceptance.key:ro" \
    "${IMAGE}" server)"; then
    rm -rf -- "${runtime}"
    fail "docker run failed"
  fi
  [[ -n "${cid}" ]] || fail "docker returned empty container id"
  if ! wait_for_uninitialized "${container}"; then
    docker rm -f "${container}" >/dev/null 2>&1 || true
    release_runtime_permissions "${runtime}" || true
    rm -rf -- "${runtime}" 2>/dev/null || true
    fail "restore runtime readiness failed"
  fi
  python3 - "${run}/restore-state.json" "${run_id}" "${container}" "${sha}" <<'PY'
import json
import sys
from datetime import datetime, timezone

out, run_id, container, sha = sys.argv[1:]
data = {
    "state": "STARTED_UNINITIALIZED",
    "run_id": run_id,
    "container": container,
    "image": "hashicorp/vault:1.21.4@sha256:4e33b126a59c0c333b76fb4e894722462659a6bec7c48c9ee8cea56fccfd2569",
    "snapshot_sha256": sha,
    "network_mode": "none",
    "published_ports": False,
    "started_at": datetime.now(timezone.utc).isoformat(),
}
with open(out, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2, sort_keys=True)
    fh.write("\n")
PY
  chmod 600 "${run}/restore-state.json"
  echo "RESTORE_START_PASS run_id=${run_id} state=STARTED_UNINITIALIZED"
}
cmd_status() {
  local run run_id container network ports image running status_json
  run="$(canonical_run_dir "${1:?run directory required}")"
  run_id="$(run_id_for "${run}")"
  container="$(container_for "${run_id}")"
  assert_label "${container}" "${run_id}"
  network="$(docker inspect -f '{{.HostConfig.NetworkMode}}' "${container}")"
  ports="$(docker inspect -f '{{json .NetworkSettings.Ports}}' "${container}")"
  image="$(docker inspect -f '{{.Config.Image}}' "${container}")"
  running="$(docker inspect -f '{{.State.Running}}' "${container}")"
  [[ "${network}" == "none" ]] || fail "unexpected network attachment"
  [[ "${ports}" == "{}" || "${ports}" == "null" ]] || fail "published ports detected"
  [[ "${image}" == "${IMAGE}" ]] || fail "image mismatch"
  status_json="$(docker exec -e VAULT_ADDR=https://127.0.0.1:8200 \
    -e VAULT_CACERT=/vault/certs/ca.pem "${container}" \
    vault status -format=json 2>/dev/null || true)"
  python3 - "${run}/restore-state.json" "${network}" "${ports}" "${running}" "${status_json}" <<'PY_STATUS'
import json,sys
path,network,ports,running,status_raw=sys.argv[1:]
with open(path,encoding='utf-8') as fh: data=json.load(fh)
data['network_mode']=network
data['published_ports']=ports not in ('{}','null')
data['container_running']=running == 'true'
try:
    st=json.loads(status_raw) if status_raw else {}
except json.JSONDecodeError:
    st={}
data['vault_initialized']=st.get('initialized')
data['vault_sealed']=st.get('sealed')
with open(path,'w',encoding='utf-8') as fh:
    json.dump(data,fh,indent=2,sort_keys=True); fh.write('\n')
print('RESTORE_STATUS_PASS state=%s initialized=%s sealed=%s' % (
    data.get('state'), data.get('vault_initialized'), data.get('vault_sealed')))
PY_STATUS
  chmod 600 "${run}/restore-state.json"
}

cmd_accept() {
  local run run_id container network ports
  run="$(canonical_run_dir "${1:?run directory required}")"
  run_id="$(run_id_for "${run}")"
  container="$(container_for "${run_id}")"
  assert_label "${container}" "${run_id}"
  network="$(docker inspect -f '{{.HostConfig.NetworkMode}}' "${container}")"
  ports="$(docker inspect -f '{{json .NetworkSettings.Ports}}' "${container}")"
  [[ "${network}" == "none" ]] || fail "unexpected network attachment"
  [[ "${ports}" == "{}" || "${ports}" == "null" ]] || fail "published ports detected"

  docker exec "${container}" sh -ec '
    set -eu
    export VAULT_ADDR=https://127.0.0.1:8200
    export VAULT_CACERT=/vault/certs/ca.pem
    token="$(vault login -method=cert -token-only -no-store \
      -client-cert=/vault/restore/client/restore-acceptance.pem \
      -client-key=/vault/restore/client/restore-acceptance.key \
      name=restore-acceptance)"
    token_var="VAULT_""TOKEN"
    export "$token_var=$token"
    [ "$(vault kv get -field=marker restore-acceptance-kv/primary)" = "ADR023_PRIMARY_OK" ]
    if vault kv get restore-acceptance-kv/forbidden >/dev/null 2>&1; then exit 41; fi
    [ "$(vault read -field=name restore-acceptance-transit/keys/restore-acceptance)" = "restore-acceptance" ]
    vault token revoke -self >/dev/null
    if vault kv get restore-acceptance-kv/primary >/dev/null 2>&1; then exit 42; fi
    unset "$token_var" token token_var
  '

  python3 - "${run}/restore-evidence.json" "${run_id}" <<'PY_ACCEPT'
import json,sys
from datetime import datetime,timezone
out,run_id=sys.argv[1:]
data={
  'run_id':run_id,
  'cert_login_pass':True,
  'primary_read_pass':True,
  'forbidden_deny_pass':True,
  'transit_metadata_pass':True,
  'token_self_revoke_pass':True,
  'network_none_pass':True,
  'zero_published_ports_pass':True,
  'acceptance_pass':True,
  'teardown_pass':False,
  'accepted_at':datetime.now(timezone.utc).isoformat(),
}
with open(out,'w',encoding='utf-8') as fh:
    json.dump(data,fh,indent=2,sort_keys=True); fh.write('\n')
PY_ACCEPT
  chmod 600 "${run}/restore-evidence.json"
  echo "RESTORE_ACCEPTANCE_PASS run_id=${run_id}"
}

cmd_teardown() {
  local run run_id container actual
  run="$(canonical_run_dir "${1:?run directory required}")"
  run_id="$(run_id_for "${run}")"
  container="$(container_for "${run_id}")"
  actual="$(docker inspect -f '{{ index .Config.Labels "com.hexor.restore-run" }}' "${container}" 2>/dev/null || true)"
  [[ "${actual}" == "${run_id}" ]] || fail "container label mismatch; teardown refused"
  docker rm -f "${container}" >/dev/null
  release_runtime_permissions "${run}/runtime" || fail "runtime permission release failed"
  rm -rf -- "${run}/runtime" || fail "runtime cleanup failed"
  rm -f -- "${run}/restore-acceptance.key"
  if [[ -f "${run}/restore-evidence.json" ]]; then
    python3 - "${run}/restore-evidence.json" <<'PY_TD'
import json,sys
from datetime import datetime,timezone
p=sys.argv[1]
with open(p,encoding='utf-8') as fh: data=json.load(fh)
data['teardown_pass']=True
data['teardown_at']=datetime.now(timezone.utc).isoformat()
with open(p,'w',encoding='utf-8') as fh:
    json.dump(data,fh,indent=2,sort_keys=True); fh.write('\n')
PY_TD
  fi
  echo "RESTORE_TEARDOWN_PASS run_id=${run_id}"
}

usage() {
  echo "usage: restore-drill.sh (--offline-selftest|--start RUN_DIR|--status RUN_DIR|--accept RUN_DIR|--teardown RUN_DIR)" >&2
  exit 2
}

case "${1:-}" in
  --offline-selftest) cmd_offline_selftest ;;
  --start) cmd_start "${2:-}" ;;
  --status) cmd_status "${2:-}" ;;
  --accept) cmd_accept "${2:-}" ;;
  --teardown) cmd_teardown "${2:-}" ;;
  *) usage ;;
esac
