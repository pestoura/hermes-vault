ui = false
disable_mlock = true

listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_cert_file = "/vault/certs/vault-server.pem"
  tls_key_file  = "/vault/certs/vault-server.key"   # HITL-owned private material, see B3
  tls_disable   = false
}

storage "raft" {
  path    = "/vault/file"
  node_id = "vault-1"
}

# Shamir manual seal (default). NO auto-unseal in MVP (spec §8, ADR-002/009).
