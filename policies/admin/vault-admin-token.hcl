# JIT class: token-role lifecycle and self-token hygiene.
path "auth/token/roles" {
  capabilities = ["list"]
}
path "auth/token/roles/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "auth/token/create/hermes-vault-admin" {
  capabilities = ["update"]
}
path "auth/token/lookup-self" {
  capabilities = ["read"]
}
path "auth/token/revoke-self" {
  capabilities = ["update"]
}
