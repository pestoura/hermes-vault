# 02 — Catálogo de capacidades HashiCorp Vault

Este documento inventaria as capacidades relevantes do Vault e como podem ser aplicadas ao Jarvas/Hermes. A seleção final depende da edição instalada e dos serviços externos usados.

## 1. KV v2 — segredos estáticos versionados

### Utilização

Centralizar segredos que não possam ainda ser gerados dinamicamente:

```text
secret/jarvas/github/*
secret/jarvas/grafana/*
secret/jarvas/cloudflare/*
secret/jarvas/google/*
secret/jarvas/microsoft/*
secret/jarvas/homeassistant/*
secret/jarvas/integrations/*
```

### Benefícios

- cifragem centralizada;
- ACL por path;
- versionamento de valores;
- eliminação progressiva de `.env` dispersos;
- rotação sem alterar prompts;
- acesso auditável.

### Limitação

Guardar um PAT ou OAuth refresh token no KV não o transforma numa credencial dinâmica. A rotação continua a depender da API/provedor correspondente.

---

## 2. Dynamic Secrets

Quando o secrets engine ou plugin consegue falar com o sistema de destino, o Vault pode gerar credenciais temporárias, atribuir lease e revogá-las.

### Prioridades Jarvas/Hermes

- bases de dados suportadas;
- cloud providers suportados;
- outros sistemas suportados por engines/plugins aprovados.

### Exemplo conceptual

```text
Hermes → Vault → DB engine → user temporário TTL 30m → PostgreSQL
```

Preferência: dynamic secret > static secret sempre que operacionalmente viável.

---

## 3. PKI Secrets Engine

Usar Vault como autoridade emissora/intermediária para certificados de curta duração.

### Aplicação

- `hermes-bridge`;
- `credential-broker`;
- `ritmo`;
- dispatchers;
- Planner MCP;
- Outlook MCP;
- exporters/collectors;
- APIs internas.

### Objetivo

Evoluir comunicação service-to-service de API keys estáticas para identidade criptográfica e mTLS.

---

## 4. Transit Secrets Engine

Vault executa operações criptográficas sem expor as chaves de cifragem/signing aos consumidores.

### Casos de uso

- assinatura de execution manifests;
- HMAC de mensagens Bridge ↔ componentes;
- assinatura de evidence bundles;
- cifragem de campos sensíveis antes de persistência;
- hashing e verificação;
- key rotation centralizada.

### Regra

A aplicação envia dados para a operação criptográfica; não recebe a chave privada de Transit.

---

## 5. Response Wrapping

Usar tokens de wrapping de uso controlado/TTL curto para reduzir exposição na entrega de informação sensível entre componentes.

### Aplicação possível

```text
Vault → wrapping token → Credential Broker → Tool → unwrap uma vez
```

Adequado quando a tool precisa necessariamente de receber material secreto em vez de usar uma operação delegada.

---

## 6. Auth Methods

O Vault suporta vários mecanismos de autenticação. O desenho deve escolher o mecanismo por workload, evitando uma credencial universal.

Candidatos relevantes:

- AppRole para workloads automatizados quando não existir identidade de plataforma melhor;
- certificate auth para workloads com identidade mTLS;
- JWT/OIDC em cenários compatíveis;
- Kubernetes auth se componentes forem migrados para Kubernetes;
- token auth apenas como mecanismo interno/derivado, não como distribuição manual permanente.

---

## 7. Identity System

Entidades e grupos permitem associar identidades autenticadas por diferentes auth methods a um modelo coerente de autorização.

Aplicação futura:

- mapear `hermes-controller` como entidade;
- mapear tools/workloads por aliases;
- separar identidade humana de workload;
- suportar grupos administrativos e operacionais.

---

## 8. ACL Policies

Policies são a principal fronteira de least privilege.

Exemplo conceptual:

```hcl
path "secret/data/jarvas/grafana/read/*" {
  capabilities = ["read"]
}
```

Não criar `path "*"` para a operação normal do Hermes.

---

## 9. Token lifecycle e leases

Usar:

- TTL curto;
- max TTL;
- renewable apenas quando necessário;
- orphan tokens apenas em desenhos justificados;
- revocation explícita quando uma execução termina ou é cancelada;
- lease cleanup em assurance runbooks.

---

## 10. Vault Agent

Funções relevantes:

- auto-auth;
- renovação de token;
- renovação de leases;
- templating/controlada entrega local de segredos;
- redução da lógica Vault dentro das aplicações.

### Princípio

Preferir Agent quando este reduzir significativamente o código de autenticação/renovação sem criar ficheiros persistentes inseguros.

---

## 11. Audit Devices

Vault deve ter pelo menos um audit device operacional antes da migração de segredos relevantes.

Registar:

- autenticações;
- acessos a paths;
- criação/revogação de leases;
- alterações de policies/auth methods;
- operações Transit/PKI relevantes.

Os logs devem ser enviados para a stack de observabilidade sem expor material secreto.

---

## 12. Integrated Storage (Raft)

Baseline recomendado para o Jarvas: Integrated Storage, evitando introduzir Consul apenas para suportar o Vault.

Requisitos:

- filesystem seguro;
- backups/snapshots;
- restore testado;
- monitorização de saúde e capacidade;
- permissões de host restritas.

---

## 13. SSH Secrets Engine

Pode ser avaliado para acesso SSH controlado, dependendo do modelo operacional pretendido. Não deve ser introduzido apenas por existir; precisa de caso de uso claro e comparação com o acesso administrativo atual.

---

## 14. TOTP Secrets Engine

Pode gerar/validar Time-based One-Time Passwords em cenários específicos. Não substitui automaticamente MFA de plataformas externas e não deve ser usado para contornar MFA interativo exigido por terceiros.

---

## 15. Plugins

Vault suporta plugins para ampliar auth/secrets engines.

Regras para Jarvas/Hermes:

- apenas plugins necessários;
- provenance validada;
- versões fixadas;
- checksums verificados;
- atualização controlada;
- sem instalar plugin apenas para evitar uma integração simples e auditável no Credential Broker.

---

## 16. Enterprise / HCP — capacidades a avaliar, não assumir

Algumas capacidades avançadas exigem Vault Enterprise/HCP, por exemplo namespaces e replicação avançada. O baseline inicial deve ser concebido para funcionar com a edição escolhida sem depender silenciosamente de funcionalidades licenciadas.

Potenciais capacidades futuras se justificadas:

- namespaces / secure multi-tenancy;
- disaster recovery replication;
- performance replication;
- control groups;
- Sentinel/governance avançada;
- HSM/KMS integrations e outros controlos Enterprise conforme requisitos.

## Matriz de prioridade

| Capacidade | Prioridade | Fase inicial |
|---|---:|---|
| KV v2 | P0 | Sim |
| Auth + identities + ACL | P0 | Sim |
| Audit | P0 | Sim |
| Integrated Storage + snapshots | P0 | Sim |
| Vault Agent | P1 | Sim, onde adequado |
| Transit | P1 | Sim |
| PKI/mTLS | P1 | Sim, após baseline |
| Dynamic DB secrets | P1 | Se houver alvo suportado |
| Response wrapping | P1 | Credential Broker |
| JIT admin | P1 | Após policies estáveis |
| SSH/TOTP | P2 | Apenas com caso de uso |
| Enterprise features | P3 | Apenas se requisitos justificarem |
