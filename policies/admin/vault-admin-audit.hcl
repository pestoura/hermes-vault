# JIT class: audit-device lifecycle only.
path "sys/audit" {
  capabilities = ["read", "list", "sudo"]
}
path "sys/audit/*" {
  capabilities = ["create", "read", "update", "delete", "sudo"]
}
