# 10 — Operação e runbooks

## Objetivo

Catalogar os runbooks operacionais do Vault partilhado. O core é `VAULT_CORE_OPERATIONAL=VERIFIED`; alguns runbooks estão ativos e outros permanecem capacidades futuras.


## Estado operacional atual

| Runbook/capacidade | Estado |
|---|---|
| Readiness 24/7 | ACTIVE — `hermes-vault-readiness.timer` |
| Scheduled encrypted snapshot | ACTIVE — ver `docs/runbooks/scheduled-snapshot.md` |
| JIT admin bootstrap | VERIFIED — revalidação live de self-revoke pendente |
| Isolated restore drill | VERIFIED — `RESTORE_DRILL_PASS` |
| HSL consumer migration | NOT_RUN |
| PKI/mTLS operations | NOT_RUN |

## RB-VAULT-001 — Daily Operational Assurance

Executado por `jarvas-operations` em modo read-only por defeito.

### Controlos

1. health endpoint responde;
2. Vault está initialized;
3. Vault não está sealed;
4. storage/raft está saudável;
5. audit device está operacional;
6. auth methods esperados estão presentes;
7. secrets engines esperados estão presentes;
8. policies críticas correspondem ao baseline;
9. não existem tokens/leases anómalos conhecidos;
10. certificados/CA não estão perto de expirar;
11. snapshot recente existe;
12. Credential Broker acceptance test passa;
13. nenhum secret é devolvido na evidência.

### Resultado

```text
PASS     — todos os controlos críticos OK
DEGRADED — operação possível, follow-up necessário
FAIL     — risco operacional/segurança; automação mutável deve parar
```

---

## RB-VAULT-002 — Safe Restart

1. confirmar snapshot recente;
2. confirmar que não existe operação administrativa em curso;
3. registar maintenance evidence;
4. restart controlado;
5. validar sealed/active state;
6. validar audit;
7. executar synthetic auth;
8. executar secret metadata test;
9. executar Transit verify test;
10. declarar PASS apenas após acceptance.

---

## RB-VAULT-003 — Secret Rotation

Para segredo estático externo:

1. identificar consumidores;
2. gerar/rodar credencial no sistema externo;
3. escrever nova versão no Vault;
4. validar consumidores;
5. revogar credencial antiga;
6. validar ausência de uso da antiga;
7. produzir evidence sem valores secretos.

Preferir dual-secret overlap curto quando o provedor o suportar.

---

## RB-VAULT-004 — Workload Identity Rotation

1. criar nova identidade/material de bootstrap;
2. limitar TTL e scope;
3. atualizar workload;
4. validar autenticação;
5. revogar material antigo;
6. confirmar que o antigo falha;
7. fechar evidence.

---

## RB-VAULT-005 — Lease Cleanup

Objetivo: eliminar credentials temporárias residuais.

1. correlacionar leases com executions ativas;
2. identificar lease órfã/expirada;
3. confirmar que não existe run legítima dependente;
4. revogar;
5. validar cleanup;
6. registar contagem e causa.

Nunca executar revogação massiva sem dry-run e scope explícito.

---

## RB-VAULT-006 — Policy Drift

1. exportar metadata/policy atual sem secrets;
2. comparar com baseline Git;
3. classificar drift:
   - expected/pending rollout;
   - unauthorized;
   - emergency change;
4. bloquear promoção se drift crítico;
5. restaurar baseline apenas com mutation gate;
6. negative tests;
7. evidence.

---

## RB-VAULT-007 — PKI Expiry / Renewal

1. verificar CA/intermediate expiry;
2. listar certificados/roles críticos;
3. renovar workload certs antes do threshold;
4. validar mTLS;
5. revogar material antigo se necessário;
6. testar CRL/status;
7. evidence.

---

## RB-VAULT-008 — Transit Key Rotation

1. confirmar consumidores e compatibilidade;
2. criar nova key version;
3. alterar versão de encrypt/sign quando adequado;
4. validar decrypt/verify histórico;
5. atualizar baseline;
6. não elevar `min_*_version` antes de validar dados antigos;
7. evidence.

---

## RB-VAULT-009 — Snapshot & Restore Drill

1. gerar snapshot;
2. copiar para armazenamento seguro;
3. verificar checksum;
4. criar ambiente isolado;
5. restaurar;
6. executar acceptance suite;
7. destruir ambiente;
8. registar RTO/RPO observado e resultado.

---

## RB-VAULT-010 — Suspected Compromise

1. bloquear identity suspeita;
2. revogar tokens/leases;
3. rodar secrets estáticos afetados;
4. recolher audit evidence;
5. verificar acessos laterais;
6. reemitir workload identity;
7. validar negative tests;
8. reativar de forma controlada.

---

## RB-VAULT-011 — JIT Admin Operation

1. produzir plano imutável/hash;
2. identificar endpoints/capabilities necessárias;
3. obter approval;
4. emitir identidade/token L3 curto;
5. executar alteração;
6. read-back;
7. acceptance/negative tests;
8. revogar L3;
9. assinar evidence.

---

## RB-VAULT-012 — Break Glass

Este runbook deve ter cópia offline.

1. declarar incidente/necessidade;
2. recuperar quorum/material autorizado;
3. gerar root temporário se necessário;
4. executar apenas reparação prevista;
5. restaurar admin normal;
6. revogar root;
7. rodar material que possa ter sido exposto;
8. rever audit;
9. documentar e fechar.

## Self-healing

Pode existir self-healing apenas para ações de baixo risco e reversíveis, por exemplo:

- reiniciar Vault Agent;
- renovar certificados de workload dentro da role existente;
- limpar lease explicitamente expirada e correlacionada;
- recuperar configuração local derivada de baseline.

Não fazer self-healing autónomo de:

- root/recovery;
- alterações de policies permissivas;
- mount/unmount de engines;
- CA replacement;
- mass revocation;
- alteração de auth methods críticos.

---

## RB-VAULT-013 — Scheduled Encrypted Snapshot

Implementado por `hermes-vault-snapshot.timer` / `hermes-vault-snapshot.service`. O fluxo usa AppRole `vault-backup`, token curto, strict TLS, snapshot Raft, checksum plaintext, cópia cifrada AES-256-CBC/PBKDF2, checksum cifrado, self-revoke e cleanup de runtime credentials. Procedimento canónico: `docs/runbooks/scheduled-snapshot.md`.
