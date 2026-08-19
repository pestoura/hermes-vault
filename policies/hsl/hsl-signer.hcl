# EXACT-PATH policy for the HSL signer AppRole. No wildcard, no sudo (spec §11.3).
path "transit/sign/hsl-transit/hsl-signing" {
  capabilities = ["update"]
}
path "transit/verify/hsl-transit/hsl-signing" {
  capabilities = ["update"]
}
path "transit/keys/hsl-transit/hsl-signing" {
  capabilities = ["read"]
}
# Explicitly NO path "sys/*", NO path "auth/*", NO other consumers' mounts.
