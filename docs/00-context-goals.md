# 00 — Contexto, objetivos e âmbito

## Contexto

O Jarvas/Hermes já deixou de ser apenas um agente que executa comandos. O ecossistema inclui Hermes MCP Bridge, RITMO, dispatchers, GitHub, Grafana, Cloudflare, Google, Microsoft, Home Assistant e outros serviços, com tendência para aumentar o número de tools autenticadas e executar operações diretamente sem passar sempre pelo LLM intermédio do Hermes.

Esse crescimento cria um problema estrutural: quanto mais autonomia operacional é dada ao ChatGPT/Hermes, maior pode ser a concentração e dispersão de credenciais estáticas.

Este projeto introduz o HashiCorp Vault como **Secrets, Identity & Trust Plane**.

## Objetivos

1. Centralizar segredos estáticos que ainda sejam necessários.
2. Eliminar progressivamente credenciais permanentes onde existam alternativas temporárias.
3. Dar identidade própria a cada workload/tool/MCP.
4. Aplicar autorização por policy e path, com mínimo privilégio.
5. Permitir privilege elevation Just-In-Time (JIT) para ações administrativas.
6. Separar administração normal de break-glass/root/recovery.
7. Emitir e renovar certificados para mTLS entre componentes.
8. Disponibilizar criptografia, signing, HMAC e hashing através do Transit Engine.
9. Produzir evidência auditável para operações de segurança e automação.
10. Integrar a camada de credenciais com a Hermes Bridge V2 e o direct-tool execution.
11. Permitir rotação e revogação rápida sem alterar prompts ou expor segredos ao modelo.
12. Tornar possível aumentar a autonomia do ChatGPT/Hermes sem aumentar na mesma proporção a exposição de credenciais.

## Não-objetivos iniciais

- Não usar Vault como substituto do IAM de cada plataforma externa.
- Não assumir que todos os tokens externos podem ser convertidos em dynamic secrets.
- Não colocar o root token no Hermes.
- Não criar um cluster Enterprise ou HA complexo antes de existir necessidade operacional.
- Não migrar todos os segredos num único cutover.
- Não guardar segredos reais no GitHub.

## Princípio de confiança

```text
ChatGPT pode pedir uma operação.
Hermes identifica e classifica a operação.
Policy decide se é permitida.
Vault disponibiliza apenas a capacidade necessária.
Executor usa essa capacidade.
Audit regista o acesso.
Lease/TTL termina ou a credencial é revogada.
```

## Critério de sucesso

A solução está bem implementada quando a maioria das operações normais do Jarvas/Hermes consegue ser executada sem que:

- o modelo conheça tokens;
- a Bridge mantenha um token global com acesso transversal;
- cada novo MCP introduza manualmente um `.env` com credenciais permanentes;
- uma única credencial comprometida permita acesso a todos os serviços.

## Estratégia de adoção

A implementação será progressiva e orientada a risco:

1. inventário;
2. Vault baseline;
3. identidade de workloads;
4. KV v2 para segredos estáticos existentes;
5. Credential Broker;
6. PKI/Transit;
7. dynamic secrets onde suportado;
8. JIT admin;
9. migração e remoção de segredos legados;
10. hardening, backup, restore e assurance contínua.
