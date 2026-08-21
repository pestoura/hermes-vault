# Dedicated 24x7 Raft backup workload identity. No administration or consumer data access.
path "sys/storage/raft/snapshot" {
  capabilities = ["read"]
}

path "auth/token/revoke-self" {
  capabilities = ["update"]
}
