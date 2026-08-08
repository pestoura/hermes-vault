# 11 — Plano de migração dos segredos atuais

## Objetivo

Migrar de forma progressiva e reversível os segredos existentes no Jarvas/Hermes para Vault, evitando cutover global e interrupções.

## Regra principal

**Inventariar antes de migrar.** Nenhuma credencial deve ser copiada para Vault apenas porque foi encontrada no host; primeiro é necessário conhecer owner, consumidor, scope, validade, possibilidade de rotação e alternativa dinâmica.

## Fase M0 — Discovery read-only

Procurar referências, não valores:

- ficheiros `.env`;
- environment variables em systemd/Compose;
- Docker secrets/configs;
- ficheiros de configuração;
- credentials stores locais;
- scripts e crontabs;
- GitHub Actions secrets utilizados por workloads Jarvas;
- tokens configurados em MCPs;
- OAuth client/refresh material;
- certificados e private keys;
- passwords de DB;
- API keys de serviços externos.

Output sanitizado:

```yaml
- id: SEC-001
  consumer: github-tool
  provider: github
  secret_type: token
  location_type: environment
  current_location: REDACTED_REFERENCE_ONLY
  rotation_supported: true
  dynamic_candidate: false
  target_path: secret/jarvas/github/runtime
  status: discovered
```

## Fase M1 — Classificação

Classificar cada item:

| Classe | Tratamento |
|---|---|
| Static unavoidable | KV v2 + rotação |
| Static but rotatable | KV v2 + rotation runbook |
| Dynamic candidate | secrets engine/plugin |
| Certificate/private key | PKI ou gestão específica |
| Cryptographic key | Transit quando adequado |
| Bootstrap credential | wrapping/secure provisioning |
| Obsolete | revogar/eliminar, não migrar |

## Fase M2 — Pilot

Escolher uma integração de baixo risco e fácil rollback.

Critérios:

- token facilmente regenerável;
- impacto baixo;
- cliente simples;
- acceptance test disponível;
- logs sem exposição.

Não começar por root credentials, IAM crítico ou integrações sem rollback.

## Fase M3 — Dual-read / controlled cutover

Quando aplicável:

```text
1. escrever secret no Vault
2. configurar consumidor para Vault
3. validar funcionalidade
4. manter fallback legado por janela curta
5. retirar fallback
6. rodar credencial
7. confirmar que configuração antiga deixou de funcionar
```

A existência do fallback deve ser temporária e explicitamente rastreada.

## Fase M4 — Tool-by-tool migration

Ordem inicial sugerida, a validar pelo inventário real:

1. integrações de observabilidade/read-only;
2. GitHub tool/app material aplicável;
3. Cloudflare e integrações equivalentes;
4. Home Assistant;
5. Google integrations;
6. Microsoft Planner/Outlook MCP;
7. databases/dynamic secrets;
8. componentes core Hermes/RITMO;
9. certificados/mTLS internos.

A ordem real deve privilegiar menor risco + maior aprendizagem, não apenas criticidade.

## Fase M5 — Remove legacy secret stores

Após cada migração:

- remover `.env` antigo quando não necessário;
- limpar environment overrides;
- remover ficheiros plaintext;
- revogar token anterior;
- invalidar backups locais inseguros quando possível;
- confirmar que reboot não reintroduz configuração antiga;
- executar secret scanning.

## OAuth

OAuth merece tratamento próprio.

Vault pode proteger:

- client secrets;
- refresh tokens;
- bootstrap material.

Mas a emissão/refresh/revocation continua dependente do provedor. O Credential Broker pode implementar adapters específicos para Microsoft/Google e guardar apenas o material mínimo necessário.

## GitHub

Preferir GitHub App/installation tokens ou mecanismo de identidade com permissões mínimas quando isso for mais adequado do que PAT estático. Vault pode guardar bootstrap/private material e o Broker pode gerar/obter tokens efémeros através da API GitHub.

## Rollback

Cada migração deve documentar:

```text
precondition
backup/reference
new Vault path/role
consumer change
acceptance test
rollback command/procedure
old credential revocation point
```

## Definition of Done por secret

- [ ] inventory atualizado;
- [ ] owner/consumer identificado;
- [ ] target model escolhido;
- [ ] policy mínima criada;
- [ ] credential no Vault ou dynamic engine configurado;
- [ ] consumidor migrado;
- [ ] acceptance positivo;
- [ ] negative test;
- [ ] logs sanitizados;
- [ ] credencial legada revogada/removida;
- [ ] restart test;
- [ ] evidence registada.
