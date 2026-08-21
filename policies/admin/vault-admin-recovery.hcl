# ADR-023 JIT recovery class: synthetic fixture lifecycle + snapshot read only.
path "sys/storage/raft/snapshot" {
  capabilities = ["read"]
}

path "sys/mounts/restore-acceptance-kv" {
  capabilities = ["create", "read", "update", "delete", "sudo"]
}

path "sys/mounts/restore-acceptance-transit" {
  capabilities = ["create", "read", "update", "delete", "sudo"]
}

path "sys/policies/acl/restore-acceptance-test" {
  capabilities = ["create", "read", "update", "delete"]
}

path "auth/cert/certs/restore-acceptance" {
  capabilities = ["create", "read", "update", "delete"]
}
path "restore-acceptance-kv/data/primary" {
  capabilities = ["create", "read", "update", "delete"]
}

path "restore-acceptance-kv/data/forbidden" {
  capabilities = ["create", "read", "update", "delete"]
}

path "restore-acceptance-transit/keys/restore-acceptance" {
  capabilities = ["create", "read", "update", "delete"]
}

path "auth/token/revoke-self" {
  capabilities = ["update"]
}
