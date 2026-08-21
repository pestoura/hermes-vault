# JIT class: authentication method and role administration only.
path "sys/auth" {
  capabilities = ["read", "list"]
}
path "sys/auth/*" {
  capabilities = ["create", "read", "update", "delete", "sudo"]
}
path "auth/cert/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "auth/approle/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# Minimal JIT lifecycle: permit the current token to retire itself without default policy.
path "auth/token/revoke-self" {
  capabilities = ["update"]
}
