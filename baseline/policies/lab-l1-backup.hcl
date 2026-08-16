# LAB_L1 manual backup identity.
# It may save a Raft snapshot and nothing else.
path "sys/storage/raft/snapshot" {
  capabilities = ["read"]
}
