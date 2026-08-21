# Security Policy

## Scope

Este repositório contém arquitetura, documentação, exemplos de policies e futura implementação do Hermes Vault.

## Regra absoluta

**Nunca colocar valores secretos neste repositório.**

Isto inclui:

- Vault root tokens;
- recovery/unseal keys ou shares;
- AppRole SecretIDs;
- passwords;
- PATs;
- OAuth client secrets ou refresh tokens;
- API keys;
- private keys;
- wrapped secrets utilizáveis;
- credenciais de bases de dados;
- ficheiros de configuração com segredos reais.

## Material TLS do Vault (HITL / custódia do operador)

A chave privada TLS do Vault é gerada e custodiada pelo operador em
`deployments/vault/certs/` (git-ignored, via `provision-tls.sh`); nunca é
commitada. A recuperação deste material TLS é responsabilidade do operador
(spec §25.4). A geração da chave/certificado é um passo HITL (operator-only) e
não é executada por tarefas não assistidas nem por CI.

## Exemplos e testes

Usar apenas:

- placeholders claramente fictícios;
- nomes de paths;
- metadata sanitizada;
- fake/honey secrets gerados especificamente para testes.

## Logging

Testes e automações devem garantir que secrets não são escritos em:

- logs GitHub Actions;
- PR comments;
- Hermes/MCP output;
- evidence bundles;
- Grafana/Loki;
- terminal transcripts versionados.

## Suspected exposure

Se um segredo real for acidentalmente commitado:

1. tratar o segredo como comprometido;
2. revogar/rodar imediatamente no provider;
3. não assumir que remover o commit elimina a exposição;
4. limpar histórico quando adequado;
5. verificar clones/artifacts/logs;
6. registar incidente e causa;
7. reforçar secret scanning/pre-commit controls.

## Privileged changes

Alterações futuras a:

- root/recovery design;
- admin policies;
- PKI CA hierarchy;
- audit configuration;
- auth methods;
- secrets engines;
- JIT privilege model;

 devem passar por revisão e acceptance/negative tests antes de produção.
