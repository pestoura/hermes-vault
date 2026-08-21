# ADR-023 restored-snapshot acceptance identity: positive + explicit negative proof.
path "restore-acceptance-kv/data/primary" {
  capabilities = ["read"]
}

path "restore-acceptance-kv/data/forbidden" {
  capabilities = ["deny"]
}

path "restore-acceptance-transit/keys/restore-acceptance" {
  capabilities = ["read"]
}

path "auth/token/revoke-self" {
  capabilities = ["update"]
}
