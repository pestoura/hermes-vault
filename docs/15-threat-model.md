# 15 — Threat model do Hermes Vault

## Ativos críticos

- segredos estáticos e dinâmicos;
- tokens Vault e leases;
- recovery/unseal material;
- root tokens temporários;
- private keys PKI;
- Transit keys;
- policies e auth configuration;
- audit logs;
- snapshots;
- identidade dos workloads;
- execution/evidence manifests.

## Ameaças principais

### T1 — Compromisso do ChatGPT/MCP session context

**Risco:** tentativa de obter tokens/secrets através de prompts, tool outputs ou logs.

**Controlos:**

- NO SECRET TO MODEL;
- Broker abstrai material sensível;
- redaction;
- outputs sanitizados;
- sem generic secret.read.

### T2 — Compromisso da Hermes Bridge

**Risco:** usar a Bridge para pedir capabilities fora do scope.

**Controlos:**

- identidade própria;
- policies restritas;
- Risk/Policy Engine;
- JIT para administração;
- audit;
- tool identities separadas;
- tokens curtos.

### T3 — Tool/MCP comprometido

**Risco:** roubo da capability da própria tool e tentativa de movimento lateral.

**Controlos:**

- identidade/path próprios;
- capability curta;
- sem acesso a paths de outras tools;
- revogação/lease cleanup;
- mTLS.

### T4 — Host Jarvas comprometido

**Risco:** atacante com acesso privilegiado ao host pode observar processos, ficheiros temporários ou tentar atingir Vault.

**Controlos:**

- hardening host;
- filesystem permissions;
- tmpfs para material efémero;
- minimizar secrets em env/process args;
- TLS/mTLS;
- separar recovery material;
- avaliar isolamento futuro do Vault em host/VM dedicada.

**Residual risk:** root no host continua a ser uma fronteira de confiança forte num deployment single-host.

### T5 — Exfiltração via logs/evidence

**Risco:** tokens/secrets aparecem em logs, errors ou manifests.

**Controlos:**

- schema allowlist;
- redaction central;
- secret scanning;
- tests com honey/fake secrets;
- nunca serializar capability payload em evidence.

### T6 — Policy demasiado permissiva

**Risco:** wildcard/sudo permite escalada.

**Controlos:**

- policy lint;
- Git baseline;
- negative tests;
- drift detection;
- JIT policies por classe.

### T7 — Secret zero compromise

**Risco:** material usado para a primeira autenticação no Vault é roubado.

**Controlos:**

- wrapping;
- TTL/use limits;
- cert/JWT identity quando possível;
- bootstrap separado;
- rotação.

### T8 — Backup/snapshot theft

**Risco:** cópia de storage/snapshot é exfiltrada.

**Controlos:**

- cifragem do armazenamento externo;
- ACL;
- retenção mínima;
- recovery material separado;
- inventário e assurance de backups.

### T9 — Vault unavailable/sealed

**Risco:** automação deixa de conseguir executar ações dependentes de secrets.

**Controlos:**

- health monitoring;
- controlled restart;
- seal design;
- snapshots/restore;
- fail closed;
- definir explicitamente que operações read-only podem continuar sem Vault.

### T10 — Abuse de JIT admin

**Risco:** aprovação/token L3 é reutilizado ou aplicado a plano diferente.

**Controlos:**

- consume-once;
- plan hash;
- resource binding;
- TTL curto;
- non-renewable;
- revoke-after-use;
- signed evidence.

### T11 — Recovery material loss

**Risco:** perda permanente de capacidade de recuperar o Vault.

**Controlos:**

- cópias independentes;
- quorum documentado;
- teste periódico do procedimento sem expor shares;
- runbook offline.

### T12 — Supply chain Vault/plugin

**Risco:** binário/plugin malicioso ou vulnerável.

**Controlos:**

- origem oficial;
- checksum/signature validation quando disponível;
- version pinning;
- atualização controlada;
- mínimo de plugins;
- vulnerability monitoring.

## Trust assumptions iniciais

1. o host Jarvas é administrado de forma confiável;
2. GitHub privado não é secret store;
3. Vault audit/logging pode ser enviado para observabilidade após sanitização;
4. serviços externos mantêm os seus próprios IAM/authorization models;
5. Vault não corrige scopes excessivos emitidos por um provider externo.

## Riscos residuais importantes

- deployment Vault e consumers no mesmo host reduz isolamento contra root local;
- segredos externos estáticos continuam vulneráveis durante o tempo em que são válidos;
- OAuth refresh tokens podem ter longa duração dependendo do provider;
- automatizar administração aumenta impacto potencial de erro lógico, mesmo com JIT;
- recovery depende de disciplina operacional fora da plataforma.

## Evolução recomendada

Se o Vault se tornar crítico e o Jarvas crescer:

```text
single-host baseline
        ↓
separate service boundary
        ↓
dedicated VM/node
        ↓
HA/DR architecture if justified
```

A promoção deve ser motivada por risco/disponibilidade medidos, não por complexidade pela complexidade.
