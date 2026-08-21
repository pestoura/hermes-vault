# JIT class: audit-device lifecycle only.
path "sys/audit" {
  capabilities = ["read", "list", "sudo"]
}
path "sys/audit/*" {
  capabilities = ["create", "read", "update", "delete", "sudo"]
}

# Minimal JIT lifecycle: permit the current token to retire itself without default policy.
path "auth/token/revoke-self" {
  capabilities = ["update"]
}
