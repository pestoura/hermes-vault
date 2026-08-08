# 03 — Identidade, autenticação e policies

## Objetivo

Dar a cada componente do Jarvas/Hermes uma identidade própria, evitando uma credencial global partilhada.

## Identidades propostas

### Control plane

- `hermes-runtime` — runtime normal da Bridge.
- `hermes-controller` — orquestração e lifecycle de capabilities.
- `hermes-vault-admin` — identidade administrativa JIT, nunca permanente.
- `jarvas-operations` — assurance, health, snapshots e validações permitidas.

### Tool plane

- `github-tool`
- `grafana-tool`
- `cloudflare-tool`
- `planner-mcp`
- `outlook-mcp`
- `google-tool`
- `homeassistant-tool`
- `ritmo`
- identidades próprias para dispatchers que necessitem de segredos.

## Princípio de separação

```text
planner-mcp      ≠ github-tool
github-tool      ≠ grafana-tool
hermes-runtime   ≠ hermes-vault-admin
human-admin      ≠ workload-admin
root/recovery    ≠ qualquer identidade normal
```

Uma tool não deve conseguir ler paths de outra tool apenas por estar no mesmo host.

## Auth methods

### AppRole

Baseline adequado para workloads automatizados quando ainda não existe uma identidade de plataforma mais forte.

Regras:

- RoleID não é tratado como segredo equivalente ao SecretID.
- SecretID deve ser protegido, preferencialmente com wrapping/entrega controlada.
- limitar `token_ttl` e `token_max_ttl`;
- limitar CIDR quando operacionalmente estável;
- policies explícitas por role;
- rotação e revogação testadas.

### Certificate Auth

Alvo desejável após PKI estar operacional:

```text
workload → certificado curto → Vault cert auth → token Vault curto
```

Permite aproximar identidade de workload e mTLS.

### JWT/OIDC

Avaliar para componentes com emissor de identidade confiável, CI/CD ou ambientes futuros em que JWT seja a melhor primitive.

### Kubernetes Auth

Se componentes forem executados em Kubernetes, preferir identidade nativa do workload a transportar AppRole secrets para pods.

## Estrutura de paths proposta

```text
secret/
└── jarvas/
    ├── github/
    ├── grafana/
    ├── cloudflare/
    ├── microsoft/
    │   ├── planner/
    │   └── outlook/
    ├── google/
    ├── homeassistant/
    └── integrations/

pki/
├── root/                  # se aplicável ao desenho escolhido
└── jarvas-intermediate/

transit/
├── hermes-execution-signing
├── hermes-evidence-signing
├── hermes-hmac
└── sensitive-field-encryption
```

## Policies propostas

### Runtime

`hermes-runtime`:

- autenticar;
- consultar apenas metadata/health necessária;
- solicitar capabilities através do Credential Broker;
- não ler todos os secrets paths diretamente.

### Controller

`hermes-controller`:

- lifecycle de leases/tokens dentro de paths autorizados;
- capability orchestration;
- revoke/renew quando previsto;
- nunca possuir `sudo` Vault ou wildcard global.

### Tool policies

Exemplo conceptual:

```hcl
# github-tool
path "secret/data/jarvas/github/runtime/*" {
  capabilities = ["read"]
}

path "secret/metadata/jarvas/github/runtime/*" {
  capabilities = ["read", "list"]
}
```

Uma policy real deve ser ainda mais restrita quando a API e o modelo de segredos o permitirem.

### Admin JIT

`hermes-vault-admin` pode incluir endpoints administrativos necessários para a alteração concreta, mas deve:

- ser emitida apenas após policy/risk decision;
- ter TTL curto;
- não ser renewable por defeito;
- ser revogada após a operação;
- produzir audit trail e evidence reforçados.

## Matriz inicial de acesso

| Identidade | KV próprio | Transit | PKI | Leases | Policies/Auth config |
|---|---|---|---|---|---|
| hermes-runtime | Não direto por defeito | verify quando necessário | Não | limitado | Não |
| hermes-controller | mediado | sign/verify definidos | request definido | gerir autorizados | Não por defeito |
| github-tool | github/* | Não | opcional | próprio | Não |
| grafana-tool | grafana/* | Não | opcional | próprio | Não |
| planner-mcp | microsoft/planner/* | Não | opcional | próprio | Não |
| outlook-mcp | microsoft/outlook/* | Não | opcional | próprio | Não |
| jarvas-operations | backup/health metadata | verify | monitor | cleanup controlado | Não |
| hermes-vault-admin | conforme ação JIT | admin necessário | admin necessário | admin necessário | Sim, apenas JIT |
| root/recovery | total | total | total | total | break-glass |

## Policy linting e CI

As policies versionadas no futuro devem passar por:

1. syntax validation;
2. proibição de wildcard global não aprovado;
3. deteção de `sudo` capability;
4. comparação com baseline;
5. teste positivo de operações autorizadas;
6. teste negativo de operações proibidas;
7. revisão antes de promoção.

## Regra crítica

O `hermes-controller` deve poder **pedir** e **orquestrar** capacidades, mas isso não implica conseguir ler indiscriminadamente cada segredo em claro. Sempre que possível, a tool autentica-se diretamente ou recebe uma capability de uso restrito através do Broker.
