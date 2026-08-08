# EXAMPLE ONLY — deliberately narrow controller policy.
# The controller orchestrates capabilities; it should not have wildcard read access to all secrets.

# Example lease lifecycle scope. Exact endpoints must be validated against the installed Vault version.
path "sys/leases/lookup/*" {
  capabilities = ["update"]
}

path "sys/leases/revoke/*" {
  capabilities = ["update"]
}

# Example access to Transit operations that are explicitly delegated to the controller.
path "transit/sign/hermes-execution-signing" {
  capabilities = ["update"]
}

path "transit/verify/hermes-execution-signing" {
  capabilities = ["update"]
}

# No path "*" and no sudo capability in the normal controller baseline.
