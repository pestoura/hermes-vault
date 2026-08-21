# ADR-022: certificate identity may only mint a token against the canonical JIT role.
path "auth/token/create/hermes-vault-admin" {
  capabilities = ["update"]
}
