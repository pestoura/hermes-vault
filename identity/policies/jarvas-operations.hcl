# Jarvas operations receives no direct secret access in EPIC-02.
path "auth/token/lookup-self" {
  capabilities = ["read"]
}

path "sys/capabilities-self" {
  capabilities = ["update"]
}
