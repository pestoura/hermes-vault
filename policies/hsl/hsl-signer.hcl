# EXACT-PATH policy for the HSL signer AppRole. No wildcard, no sudo (spec §11.3).
# Paths bind the accepted E1 canonical mount `hsl-transit` and key `hsl-signing`.
path "hsl-transit/sign/hsl-signing" {
  capabilities = ["update"]
}
path "hsl-transit/verify/hsl-signing" {
  capabilities = ["update"]
}
path "hsl-transit/keys/hsl-signing" {
  capabilities = ["read"]
}
# Explicitly NO path "sys/*", NO path "auth/*", NO other consumers' mounts.
