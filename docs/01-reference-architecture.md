# 01 — Arquitetura de referência

## Visão lógica

```mermaid
flowchart TD
    U[Utilizador] --> C[ChatGPT]
    C --> B[Hermes MCP Bridge V2]
    B --> PL[Intent / Batch Planner]
    PL --> PE[Policy & Risk Engine]
    PE --> EX[Execution Orchestrator]
    EX --> CB[Credential Broker]
    CB --> V[HashiCorp Vault]

    V --> A[Auth Methods]
    V --> KV[KV v2]
    V --> PKI[PKI Secrets Engine]
    V --> TR[Transit Secrets Engine]
    V --> DB[Dynamic Secrets]
    V --> AD[Audit Devices]

    CB --> T1[GitHub Tool]
    CB --> T2[Grafana Tool]
    CB --> T3[Cloudflare Tool]
    CB --> T4[Planner MCP]
    CB --> T5[Outlook MCP]
    CB --> T6[Home Assistant]
    CB --> T7[RITMO / Dispatchers]

    T1 --> E[Evidence / Result Manifest]
    T2 --> E
    T3 --> E
    T4 --> E
    T5 --> E
    T6 --> E
    T7 --> E
    TR --> E
```

## Fluxo normal L1/L2

```mermaid
sequenceDiagram
    participant U as Utilizador
    participant C as ChatGPT
    participant B as Hermes Bridge
    participant P as Policy Engine
    participant CB as Credential Broker
    participant V as Vault
    participant T as Tool Executor

    U->>C: Executa operação
    C->>B: pedido estruturado
    B->>P: classificar ação + recurso + risco
    P-->>B: ALLOW / DENY / REQUIRE_APPROVAL
    B->>CB: capability request
    CB->>V: autenticação workload + path autorizado
    V-->>CB: secret/token/cert/lease
    CB->>T: capacidade mínima
    T-->>B: resultado + evidence
    B-->>C: resultado sanitizado
    Note over CB,V: credencial expira ou é revogada
```

## Trust boundaries

### TB-1 — ChatGPT ↔ Hermes MCP Bridge

- nenhum segredo deve atravessar esta boundary;
- pedidos devem ser expressos como intenção, ação e resource scope;
- outputs devem passar por redaction/sanitização.

### TB-2 — Bridge ↔ Policy/Risk Engine

- a decisão deve considerar identidade, ação, alvo, mutability, ambiente e nível de risco;
- ações privilegiadas podem exigir approval e/ou JIT elevation.

### TB-3 — Credential Broker ↔ Vault

- autenticação machine-to-machine;
- sem root token;
- tokens com TTL e policies restritas;
- uso de Vault Agent quando reduzir complexidade e exposição.

### TB-4 — Credential Broker ↔ Tool Executor

- fornecer apenas a capacidade necessária;
- preferir referência, file descriptor, memória temporária ou response wrapping a persistência em disco;
- cleanup após execução.

### TB-5 — Vault ↔ break-glass material

- recovery/unseal/root temporário ficam fora da cadeia normal do Hermes;
- acesso apenas em recuperação ou bootstrap controlado.

## Plano físico inicial recomendado

Primeira implementação deliberadamente simples:

```text
Jarvas host
├── vault.service
├── vault-agent.service
├── hermes-bridge.service
├── credential-broker.service   # pode começar embutido na Bridge
├── ritmo.service
├── dispatchers...
└── /var/lib/vault/              # Integrated Storage, permissões restritas
```

Evolução futura possível:

```text
Vault node/cluster dedicado
        │
        ├── TLS/mTLS
        ├── Integrated Storage HA
        ├── snapshots externos
        └── eventualmente Enterprise/HCP se requisitos justificarem
```

## Separação de identidades

```mermaid
flowchart LR
    V[Vault]
    V --> HR[hermes-runtime]
    V --> HC[hermes-controller]
    V --> HVA[hermes-vault-admin JIT]
    V --> GH[github-tool]
    V --> GF[grafana-tool]
    V --> CF[cloudflare-tool]
    V --> PL[planner-mcp]
    V --> OL[outlook-mcp]
    V --> HA[homeassistant]
    V --> RT[ritmo]

    BG[Root / Recovery] -. break-glass only .-> V
```

## Modelo operacional desejado

A Bridge não pede «o token do GitHub». Pede uma capability:

```yaml
principal: hermes-controller
action: github.create_branch
resource: pestoura/example
risk: medium
requested_ttl: 5m
```

O Credential Broker resolve internamente:

1. qual identidade deve ser usada;
2. que policy permite a ação;
3. que secret engine/path contém ou gera a capacidade;
4. TTL/lease;
5. forma segura de entrega;
6. revogação/cleanup.

## Regra arquitetural

O Vault não deve tornar-se num novo monólito de confiança onde `hermes-controller` consegue ler indiscriminadamente tudo. O desenho deve privilegiar **delegação por tool identity**; o controller deve orquestrar, não concentrar todos os segredos em memória.
