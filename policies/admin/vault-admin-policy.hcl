# JIT class: ACL policy administration only.
path "sys/policies/acl" {
  capabilities = ["list"]
}
path "sys/policies/acl/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# Minimal JIT lifecycle: permit the current token to retire itself without default policy.
path "auth/token/revoke-self" {
  capabilities = ["update"]
}
