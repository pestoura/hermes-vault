# 09 — Bootstrap, unseal, recovery e break-glass

## Objetivo

Garantir que o Vault pode ser iniciado, recuperado, restaurado e administrado em emergência sem depender do ChatGPT/Hermes.

## Princípio

```text
Hermes administra operação normal.
Hermes pode obter administração L3 JIT.
Hermes NÃO possui recovery/unseal/root permanente.
```

## Bootstrap inicial

Fluxo previsto:

```mermaid
flowchart TD
    I[Install Vault] --> TLS[Configure TLS]
    TLS --> S[Configure Integrated Storage]
    S --> INIT[Initialize Vault]
    INIT --> RM[Secure recovery/unseal material]
    RM --> U[Unseal / auto-unseal design]
    U --> RT[Use initial root]
    RT --> ADM[Create human/workload admin paths]
    ADM --> AUD[Enable audit]
    AUD --> BAS[Create baseline auth/policies]
    BAS --> RV[Revoke initial root token]
```

## Seal design

A decisão live está fechada em **Shamir 3/2 manual**, sem auto-unseal. O container pode arrancar automaticamente, mas um estado sealed continua a exigir quorum operador 2/3. Nenhuma automação pode receber, reconstruir ou armazenar shares.

## Recovery material

Não guardar recovery/unseal material:

- no GitHub;
- no Vault que ele próprio desbloqueia;
- em `.env` do Jarvas;
- em scripts;
- no Hermes state DB;
- no ChatGPT;
- em logs;
- em backups não cifrados.

Modelo desejado:

```text
Recovery material
├── primary encrypted/offline copy
├── independent backup copy
└── documented quorum/procedure
```

A localização concreta não deve ser documentada neste repositório se isso aumentar o risco.

## Root

### Bootstrap

O initial root token é transitório.

```text
initialize → configure secure administration → validate → revoke root
```

### Emergency root

Quando indispensável:

```text
recovery quorum
  ↓
operator generate-root
  ↓
temporary root
  ↓
repair/recover
  ↓
validate
  ↓
revoke root
```

## Snapshots

Com Integrated Storage, definir política de snapshots.

Baseline operacional atual:

- snapshot automático diário às 02:30 local;
- identidade mínima `vault-backup`;
- retenção local de 14 gerações;
- cópia cifrada AES-256-CBC/PBKDF2;
- checksums e metadata sanitizada;
- runtime credentials efémeras via systemd;
- restore drill independente obrigatório;
- não considerar backup “válido” apenas porque o ficheiro existe.

Ver `docs/runbooks/scheduled-snapshot.md`.

## Restore test

Executar sempre em ambiente isolado/não produtivo.

Acceptance mínimo:

1. iniciar instância Vault isolada compatível;
2. restaurar snapshot;
3. validar storage/metadata;
4. autenticar com identidade de teste;
5. ler secret fictício de acceptance;
6. validar policy deny;
7. validar Transit/PKI metadata conforme aplicável;
8. destruir ambiente de teste.

Não copiar recovery/root material real para pipelines ou GitHub Actions.

### ADR-023 — execução isolada

O restore drill canónico usa o harness `docs/runbooks/restore-drill.md`. O container de teste corre com `network=none`, zero portas publicadas, imagem Vault pinned e sem volumes/redes do Vault de produção.

O repositório pode preparar snapshot cifrado/checksummed, fixtures sintéticos, runtime isolado, status, acceptance e teardown. A inicialização temporária, o `snapshot-force` e o unseal pós-restore com as **original Shamir shares** são HITL operator-only. Nenhuma share, root/token ou localização de custódia é entregue à automação.

Estado live: `VERIFIED_ADR023_LIVE_ACCEPTED`. `RESTORE_DRILL_PASS` está VERIFIED por uma execução real que completou force-restore isolado, quorum Shamir original, acceptance positiva/negativa e teardown no mesmo run. Ver `docs/evidence/2026-08-21-adr-023-live-acceptance.md`.

## Disaster scenarios

### Vault process down

- restart controlado;
- verificar storage;
- validar sealed state;
- validar audit e auth;
- acceptance test.

### Host loss

- reconstruir host a partir de IaC/config baseline;
- recuperar TLS/bootstrap prerequisites;
- restaurar snapshot;
- recuperar/unseal de forma controlada;
- reemitir workload identities se necessário.

### Credential compromise

- revogar token/lease;
- desativar AppRole/cert/identity afetada;
- rodar segredo externo se estático;
- rever audit;
- reemitir identidade;
- assinar evidence do incidente/recuperação.

### Policy compromise/misconfiguration

- bloquear identidade afetada;
- comparar com baseline Git;
- restaurar policy conhecida;
- executar negative tests;
- só depois reativar automação.

### Loss of all normal admins

- acionar break-glass;
- usar recovery quorum;
- gerar root temporário;
- recriar administração normal;
- revogar root;
- produzir evidence.

## Runbook offline

Deve existir uma versão exportável/offline do procedimento de recuperação para utilização quando GitHub/Hermes não estiverem acessíveis.

## Gate obrigatória antes de produção

A gate de recovery do **Vault core** está satisfeita por `RESTORE_DRILL_PASS`. Consumer production enablement continua separado; `FIRST_CONSUMER_BOOTSTRAP=NOT_RUN` e `UNSEALED_READY=false` até acceptance do primeiro consumer.
