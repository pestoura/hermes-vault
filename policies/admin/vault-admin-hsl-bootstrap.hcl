# JIT class: bootstrap only the dedicated HSL Transit mount/key.
# No wildcard and no delete capability: this identity cannot affect other mounts.
path "sys/mounts" {
  capabilities = ["read", "list"]
}

# Manage only the exact HSL mount path; no wildcard or sudo is required.
path "sys/mounts/hsl-transit" {
  capabilities = ["create", "read", "update"]
}

# Create/read/update only the exact HSL signing key. No sudo is required here.
path "hsl-transit/keys/hsl-signing" {
  capabilities = ["create", "read", "update"]
}

# Minimal JIT lifecycle: permit the current token to retire itself.
path "auth/token/revoke-self" {
  capabilities = ["update"]
}
