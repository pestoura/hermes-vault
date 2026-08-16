# GitHub tool has one exact KV v2 runtime path and self-introspection only.
path "auth/token/lookup-self" {
  capabilities = ["read"]
}

path "sys/capabilities-self" {
  capabilities = ["update"]
}

path "secret/data/jarvas/github/runtime" {
  capabilities = ["read"]
}

path "secret/metadata/jarvas/github/runtime" {
  capabilities = ["read"]
}
