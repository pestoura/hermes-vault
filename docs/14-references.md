# 14 — Referências oficiais

Utilizar preferencialmente documentação oficial HashiCorp durante a implementação. Confirmar sempre a versão instalada, porque endpoints, defaults e capacidades podem evoluir.

## Vault core

- Vault documentation: https://developer.hashicorp.com/vault/docs
- Secrets engines: https://developer.hashicorp.com/vault/docs/secrets
- Auth methods: https://developer.hashicorp.com/vault/docs/auth
- Policies: https://developer.hashicorp.com/vault/docs/concepts/policies
- Tokens: https://developer.hashicorp.com/vault/docs/concepts/tokens
- Response wrapping: https://developer.hashicorp.com/vault/docs/concepts/response-wrapping

## Storage / operations

- Integrated Storage: https://developer.hashicorp.com/vault/docs/configuration/storage/raft
- Operator commands: https://developer.hashicorp.com/vault/docs/commands/operator
- Generate root: https://developer.hashicorp.com/vault/docs/commands/operator/generate-root
- Seal best practices: https://developer.hashicorp.com/vault/docs/configuration/seal/seal-best-practices

## Agent / workload auth

- Vault Agent: https://developer.hashicorp.com/vault/docs/agent-and-proxy/agent
- AppRole: https://developer.hashicorp.com/vault/docs/auth/approle
- Certificate auth: https://developer.hashicorp.com/vault/docs/auth/cert
- JWT/OIDC auth: https://developer.hashicorp.com/vault/docs/auth/jwt
- Kubernetes auth: https://developer.hashicorp.com/vault/docs/auth/kubernetes

## Secrets engines relevantes

- KV v2: https://developer.hashicorp.com/vault/docs/secrets/kv/kv-v2
- Transit: https://developer.hashicorp.com/vault/docs/secrets/transit
- PKI: https://developer.hashicorp.com/vault/docs/secrets/pki
- Database: https://developer.hashicorp.com/vault/docs/secrets/databases
- SSH: https://developer.hashicorp.com/vault/docs/secrets/ssh
- TOTP: https://developer.hashicorp.com/vault/docs/secrets/totp

## Audit

- Audit devices: https://developer.hashicorp.com/vault/docs/audit

## Enterprise / HCP — consultar apenas se necessário

- Vault Enterprise: https://developer.hashicorp.com/vault/docs/enterprise
- Enterprise licensing: https://developer.hashicorp.com/vault/docs/license
- Namespaces: https://developer.hashicorp.com/vault/docs/enterprise/namespaces
- Replication: https://developer.hashicorp.com/vault/docs/enterprise/replication

## Regra de versão

Antes de executar qualquer implementação:

1. confirmar versão estável/suportada pretendida;
2. rever release notes/security advisories;
3. confirmar quais as features Community vs Enterprise/HCP;
4. fixar versão no deployment;
5. registar ADR se uma funcionalidade licenciada passar a ser requisito.
