# Retomar implementação do Hermes Vault

Este ficheiro é o ponto de entrada para uma futura sessão ChatGPT/Hermes.

## Pedido de retoma esperado

O utilizador pode dizer apenas:

> **Vamos implementar o HashiCorp Vault.**

## Instruções para o controlador

1. Ler `README.md`.
2. Ler `docs/12-implementation-roadmap.md`.
3. Ler `IMPLEMENTATION-CHECKLIST.md`.
4. Ler `docs/13-security-decisions.md` e `docs/15-threat-model.md`.
5. Consultar as issues abertas do repositório.
6. Confirmar o estado real do Jarvas/Hermes por discovery read-only; não assumir que o host continua igual ao momento em que este blueprint foi criado.
7. Iniciar na primeira fase/EPIC ainda não concluída.
8. Avançar automaticamente quando as gates estiverem GREEN/PASS.
9. Parar apenas perante blocker real, necessidade de break-glass ou decisão de risco que exija intervenção explícita.

## Guardrails obrigatórios

```text
NO SECRET TO THE MODEL
IDENTITY + POLICY PER TOOL
SHORT-LIVED CAPABILITY WHEN POSSIBLE
JIT PRIVILEGE ELEVATION
ROOT IS BREAK-GLASS ONLY
AUDIT EVERYTHING
FAIL CLOSED
```

## Primeira ação técnica quando a implementação começar

Executar **Phase 0 — Discovery & prerequisites** em modo read-only:

- versão/estado real do host Jarvas;
- serviços Hermes/RITMO/Bridge/dispatchers;
- secret references e consumidores, sem recolher valores para logs/chat;
- current TLS/certificates;
- storage disponível;
- backup/recovery constraints;
- integrações atuais GitHub/Grafana/Cloudflare/Google/Microsoft/Home Assistant;
- versão/edição Vault a instalar;
- decisão de seal/unseal.

Preencher `templates/secret-inventory.yaml` apenas com metadata sanitizada.

## Gate de entrada

Não instalar nem migrar segredos enquanto Phase 0 não produzir:

```text
DISCOVERY_COMPLETE
NO_SECRET_IN_REPO
TARGET_ARCHITECTURE_APPROVED
RECOVERY_DESIGN_DEFINED
```

## Fonte canónica

Se existir divergência entre uma conversa antiga e o repositório, usar:

1. estado real observado no ambiente;
2. decisões versionadas neste repositório;
3. documentação oficial Vault para a versão escolhida;
4. só depois contexto histórico de conversas.
