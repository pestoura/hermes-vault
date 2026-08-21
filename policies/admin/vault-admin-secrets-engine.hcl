# JIT class: secrets-engine mount lifecycle only; no secret-value paths.
path "sys/mounts" {
  capabilities = ["read", "list"]
}
path "sys/mounts/*" {
  capabilities = ["create", "read", "update", "delete", "sudo"]
}
