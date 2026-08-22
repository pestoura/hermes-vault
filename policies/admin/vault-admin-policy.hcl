# JIT class: ACL policy administration only.
path "sys/policies/acl" {
  capabilities = ["list"]
}
path "sys/policies/acl/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# Minimal JIT lifecycle: permit the current token to inspect and retire itself
# without granting visibility or control over any other token.
path "auth/token/lookup-self" {
  capabilities = ["read"]
}
path "auth/token/revoke-self" {
  capabilities = ["update"]
}
