# 19 — EPIC-03 VaultCredentialProvider & Hermes Bridge V2 integration

## Estado

- Design: **APPROVED — Option A**
- Implementação repository-side: **IN PROGRESS**
- Live Vault discovery/runtime: **NOT_RUN**
- Hosted CI: **BLOCKED_EXTERNAL_BILLING** enquanto o runner não iniciar por billing/spending limit
- PR #17 / `epic-03/credential-broker-core`: **SUPERSEDED ARCHITECTURE — DO NOT MERGE**

Um gate só é `PASS` quando foi executado e produziu evidência correspondente. Estado de repositório nunca promove automaticamente estado live.

## Provenance canónica

### hermes-vault

EPIC-03 é empilhado sobre:

- repository: `pestoura/hermes-vault`
- branch predecessor: `epic-02/identity-kv-contracts`
- exact SHA: `28a86a407101a16a167695191323435b867ec737`

### hermes-mcp-bridge

A integração é desenhada e testada contra:

- repository: `pestoura/hermes-mcp-bridge`
- canonical main SHA: `3717bd5469b061a44294b27e1a7510d477d3752b`

Nesse SHA já existem `ProviderCredentialBroker`, `AuthorizationHandle`, `ProviderGateway`, `V2Composition`, policy/scope/approval/audit pipeline, DIRECT/BATCH/DAG/RUNBOOK/INTEGRATIONS/HYBRID e proteção de credential domains.

## Problema

EPIC-02 definiu identidade e least privilege no Vault para workloads, incluindo `github-tool`, mas não existe ainda uma integração Vault-native da Bridge V2 que entregue autorização ao provider adapter sem expor material secreto ao modelo ou criar uma segunda arquitetura de broker.

A Bridge V2 já resolve o problema de autorização request-scoped. O EPIC-03 deve acrescentar **uma origem Vault** a essa arquitetura, não substituí-la.

## Objetivos do MVP

1. Adicionar `VaultCredentialProvider` in-process na Hermes MCP Bridge V2.
2. Preservar `ProviderCredentialBroker` como boundary de credential domain.
3. Preservar `AuthorizationHandle` como único handle entregue ao execution path.
4. Resolver credenciais por capability fechada, nunca por secret path arbitrário.
5. Provar a primeira vertical slice `github.read` até ao GitHub provider adapter com dados exclusivamente sintéticos nos testes repository-side.
6. Garantir cleanup/revoke em sucesso, erro e cancellation.
7. Garantir isolamento em múltiplas execuções/batch.
8. Garantir fail-closed quando Vault/provider está indisponível.
9. Garantir que resultados, audit e evidence permanecem sanitizados.

## Não objetivos do MVP

Ficam explicitamente fora:

- Credential Broker microservice separado;
- Unix socket broker;
- sidecar por tool;
- Vault Agent;
- Kubernetes workload identity;
- PKI;
- JIT Vault admin;
- dynamic DB credentials;
- multi-Vault;
- HA Broker;
- migração massiva de secrets;
- alteração da superfície efetiva de 27 MCP tools.

## Ownership por repositório

### `pestoura/hermes-vault`

É source-of-truth para:

- policy e AppRole contracts;
- exact provenance do LAB_L1;
- negative capability matrix;
- runbooks de bootstrap/migração/rollback/rotation;
- contratos de integração Vault;
- ADRs e security decisions;
- live evidence sanitizada quando a lane live for executada.

Não deve conter uma implementação paralela de broker, Bridge runtime ou provider adapter.

### `pestoura/hermes-mcp-bridge`

É source-of-truth para:

- `ProviderCredentialBroker`;
- `AuthorizationHandle`;
- `ProviderGateway`;
- `V2Composition`;
- `VaultCredentialProvider`;
- provider adapter integration;
- cancellation/cleanup no execution path;
- repository-side behavioral acceptance.

## Arquitetura aprovada

```text
ProviderGateway
    |
    v
ProviderCredentialBroker
    |
    | (provider_id, credential_capability_id)
    v
VaultCredentialProvider
    |
    | capability.status / capability.request / capability.revoke
    v
Vault capability client/transport
    |
    v
Vault
    |
    v
opaque capability lease/material boundary
    |
    v
AuthorizationHandle
    |
    | apply only at final execution boundary
    v
Provider Adapter
    |
    v
sanitized result + audit/evidence
    |
    v
cleanup/revoke
```

### Nota sobre capabilities GitHub

A Bridge V2 distingue:

- operation capability: `github.repo_read`;
- credential capability: `github.read`.

O EPIC-03 preserva esta distinção. Não cria `github.read` como tool nova.

## Capability surface interna

A interface inicial do Vault provider é fechada a três operações sem leitura genérica de paths:

### `capability.status(provider_id, credential_capability_id)`

Retorna apenas readiness booleana/estado sanitizado. Nunca retorna material, path físico, token, lease token ou bootstrap material.

### `capability.request(provider_id, credential_capability_id)`

Só aceita capabilities previamente configuradas e permitidas. Para a primeira slice, apenas o domínio GitHub e `github.read` são aceites. O retorno é um objeto opaco aplicável à boundary final; não existe accessor para o segredo.

### `capability.revoke(provider_id, credential_capability_id)`

Impede novas emissões e solicita cleanup/revocation de grants controlados pelo provider. O `AuthorizationHandle` request-scoped continua a ser revogado no fim de cada invocação.

Estas operações são **interfaces internas**, não endpoints MCP públicos.

## Integração com `ProviderCredentialBroker`

O broker existente mantém:

- verificação de `CredentialDomain`;
- `requested_scopes ⊆ granted_scopes`;
- rejeição de broad/admin credential;
- request-scoped handle;
- revoke de capability.

O EPIC-03 acrescenta suporte a um backend/provider configurado por par fechado `(provider_id, credential_capability_id)`. O backend Vault não pode ampliar scopes nem decidir dinamicamente paths pedidos pelo caller.

A origem file atual pode continuar suportada onde explicitamente configurada, mas **não existe fallback automático** de Vault para file/env quando a origem selecionada é Vault.

## `AuthorizationHandle` e lifecycle

O handle existente continua:

- single-use;
- deadline-bound;
- non-copyable;
- non-pickleable;
- redacted em `repr`/`str`;
- sem accessor de material.

O lifecycle deve ainda suportar um cleanup callback idempotente para que recursos da origem Vault possam ser libertados/revogados em todos os caminhos.

O `ProviderGateway` deve garantir cleanup num `finally` que cubra:

1. falha durante aplicação da autorização;
2. provider success;
3. provider refusal/error;
4. exception não tratada;
5. cancellation/interruption da execução.

Cleanup não pode depender do adapter cooperar.

## Secret boundary

É proibido expor ao modelo, canonical payload, resultado, exception, audit ou evidence:

- token;
- password;
- SecretID;
- Vault token;
- `client_secret`;
- private key;
- wrapped payload após unwrap.

O Vault provider pode manipular material apenas na boundary interna necessária para autenticação/resolução. Em testes repository-side usa-se exclusivamente material sintético sem qualquer origem real.

## Semântica Vault

A implementação do MVP usa uma porta/client injetável orientada a capability. A Bridge não recebe `secret/data/...` fornecido por callers.

O mapeamento real da capability `github.read` para o contract EPIC-02 permanece sob controlo do `hermes-vault`, cujo policy contract limita `github-tool` a:

- `secret/data/jarvas/github/runtime`;
- `secret/metadata/jarvas/github/runtime`.

A implementação repository-side não autentica no Vault real. Bootstrap AppRole, wrapped SecretID, Vault token, init/unseal e root permanecem HITL/live-lane concerns.

## Fail-closed

Quando o backend Vault está indisponível, a capability não está pronta ou o request viola domínio/scope:

- zero fallback permissivo;
- zero provider call quando a autorização não pode ser obtida;
- outcome sanitizado;
- reason code fechado;
- cleanup de qualquer grant parcialmente criado;
- nenhum material em logs/evidence.

## Batch e isolamento

Cada request/tool-call recebe grant/handle próprios. É proibido reutilizar o mesmo objeto de capability entre items do batch.

A evidência de `BATCH_EXECUTION_PASS` deve demonstrar:

- dois ou mais requests válidos;
- grants/handles distintos;
- cleanup individual;
- falha de um item não expõe nem reutiliza material de outro;
- nenhum secret-shaped field no resultado agregado.

## Audit e evidence

A Bridge continua a usar os schemas/audit pipeline existentes. O Vault provider só pode contribuir metadados sanitizados, por exemplo:

- provider id;
- credential capability id;
- readiness state;
- request/correlation id já permitido;
- cleanup outcome;
- reason code;
- scope digest já produzido pelo broker.

Não são permitidos secret paths operacionais, raw lease IDs, tokens, SecretIDs ou wrapped payloads.

## Gates repository-side EPIC-03

| Gate | Evidência mínima |
|---|---|
| `BROKER_ACCEPTANCE_PASS` | walking skeleton `github.repo_read` → `github.read` → Vault provider → handle → adapter → sanitized success |
| `NO_SECRET_TO_MODEL` | sentinel secreto ausente de payload/canonical/audit/error |
| `LEASE_CLEANUP_PASS` | cleanup exatamente uma vez após success/error |
| `CANCEL_CLEANUP_PASS` | cancellation/interruption executa cleanup |
| `BATCH_EXECUTION_PASS` | múltiplos requests com grants separados e cleanup independente |
| `SEPARATE_CAPABILITIES_PASS` | objetos/grants distintos por request/capability |
| `NO_CROSS_TOOL_SECRET_ACCESS` | tentativa cross-domain recusada antes da boundary final |
| `SANITIZED_RESULT_PASS` | result shaping remove/rejeita secret-shaped output |
| `NO_SECRET_SERIALIZATION_PASS` | handle/grant não serializável e `repr`/`str` redacted |
| `FAIL_CLOSED_VAULT_UNAVAILABLE_PASS` | Vault unavailable → refusal, zero fallback, zero provider call |

Um teste com fake/synthetic provider pode provar a propriedade repository-side. Não prova que o Vault live esteja inicializado, unsealed, autenticado ou corretamente configurado.

## Gates live — separados

A conclusão repository-side não altera:

```text
Vault runtime       = NOT_RUN
signer decision     = NO_DECISION
supplier            = NO_SELECTION
trust               = UNBOUND
promotion_allowed   = false
runtime_status      = NOT_RUN
execution_authority = NONE
campaign            = BLOCKED / HOLD
```

A lane live só pode promover estados com evidence própria:

`Phase 0 discovery → LAB_L1 → TLS → init 3/2 → unseal → audit → snapshot → AppRole → Transit → root revoke → capability evidence`.

Shamir shares, root token, SecretID, Vault token ou outros segredos exigem HITL e nunca entram em chat, GitHub, logs ou evidence.

## Rollback

Repository-side:

1. desativar seleção do Vault provider;
2. revogar grants/handles ativos;
3. manter a Bridge fail-closed;
4. reverter o commit/PR da integração sem alterar EPIC-02 policies.

Não existe fallback automático para uma origem mais permissiva.

Live rollback será definido e executado apenas após live discovery e nunca implica reconstrução/destruição de Vault sem HITL.

## PR topology

O EPIC-03 exige duas PRs coordenadas, porque a implementação não pode atravessar fronteiras de repositório:

1. `hermes-vault`: PR de contract/spec/provenance empilhada sobre a PR #16 / `epic-02/identity-kv-contracts`;
2. `hermes-mcp-bridge`: companion code PR baseada no exact SHA `3717bd5469b061a44294b27e1a7510d477d3752b`.

A PR `hermes-vault` deve referenciar o exact head aceite da companion PR. Nenhuma PR pode afirmar que um gate foi executado no outro repositório sem exact-SHA evidence.

## Self-review do design

Revisto contra `hermes-mcp-bridge@3717bd5469b061a44294b27e1a7510d477d3752b`:

- reutiliza `ProviderCredentialBroker`: **SIM**;
- reutiliza `AuthorizationHandle`: **SIM**;
- reutiliza `ProviderGateway`: **SIM**;
- não cria novo listener/service: **SIM**;
- mantém credential-domain checks: **SIM**;
- mantém `github.repo_read` vs `github.read`: **SIM**;
- não acrescenta generic secret path API: **SIM**;
- não altera automaticamente 27-tool surface: **SIM**;
- cleanup precisa de extensão mínima do handle/gateway: **SIM — previsto e coberto por TDD**;
- live authentication/secret handling requerido para repository acceptance: **NÃO**.

Resultado da self-review: **ACCEPTED para implementação TDD**.
