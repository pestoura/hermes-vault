# EXAMPLE ONLY — adapt paths/capabilities after discovery and tests.
# No real secrets are stored in this repository.

path "secret/data/jarvas/github/runtime/*" {
  capabilities = ["read"]
}

path "secret/metadata/jarvas/github/runtime/*" {
  capabilities = ["read", "list"]
}

# Explicitly do not grant access to other integrations.
