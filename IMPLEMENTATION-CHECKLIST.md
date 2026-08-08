# Hermes Vault — Implementation Checklist

Utilizar esta checklist quando a implementação for iniciada.

## 0. Pre-flight

- [ ] Ler README e `docs/12-implementation-roadmap.md`.
- [ ] Confirmar versão/edição Vault pretendida.
- [ ] Confirmar que nenhum secret real será colocado no Git.
- [ ] Criar branch de implementação.
- [ ] Registar execution/plan IDs se executado via Hermes.

## 1. Discovery

- [ ] Inventariar consumidores e secret references.
- [ ] Preencher `templates/secret-inventory.yaml` sem valores secretos.
- [ ] Classificar static/dynamic/PKI/Transit/bootstrap.
- [ ] Identificar owners e rollback.
- [ ] Mapear tool identities.

## 2. Vault baseline

- [ ] Instalar versão fixada.
- [ ] Configurar TLS.
- [ ] Configurar Integrated Storage.
- [ ] Inicializar Vault de forma controlada.
- [ ] Proteger recovery/unseal material fora do Hermes.
- [ ] Configurar audit device.
- [ ] Configurar snapshots.
- [ ] Criar administração normal.
- [ ] Revogar initial root.

## 3. Identity & policy

- [ ] Criar auth method inicial.
- [ ] Criar `hermes-runtime`.
- [ ] Criar `hermes-controller`.
- [ ] Criar `jarvas-operations`.
- [ ] Criar primeira tool identity.
- [ ] Aplicar policy mínima.
- [ ] Executar positive test.
- [ ] Executar negative test.

## 4. Pilot secret

- [ ] Selecionar integração de baixo risco.
- [ ] Criar KV path/role.
- [ ] Migrar secret piloto.
- [ ] Alterar consumidor.
- [ ] Restart test.
- [ ] Rodar/revogar secret legado.
- [ ] Secret scan.

## 5. Credential Broker

- [ ] Definir schema de capability request.
- [ ] Implementar request/status/revoke.
- [ ] Implementar redaction.
- [ ] Implementar correlation IDs.
- [ ] Implementar wrapped/memory-only delivery.
- [ ] Implementar cleanup/cancellation.
- [ ] Provar NO SECRET TO MODEL.

## 6. Hermes Bridge V2

- [ ] Integrar Risk/Policy Engine.
- [ ] Integrar Broker.
- [ ] Fast path direct-tool.
- [ ] Agent path.
- [ ] Batch multi-tool.
- [ ] Tool identities independentes.
- [ ] Evidence manifests.

## 7. Transit

- [ ] Criar keys separadas.
- [ ] Execution signing.
- [ ] Evidence signing.
- [ ] HMAC use case.
- [ ] Rotation test.
- [ ] Tamper verification.

## 8. PKI/mTLS

- [ ] Decidir root/intermediate design.
- [ ] Criar PKI roles.
- [ ] Emitir cert piloto.
- [ ] Automatizar renewal.
- [ ] Ativar mTLS num caminho interno.
- [ ] Revocation test.
- [ ] Expiry monitoring.

## 9. JIT admin

- [ ] Criar admin policy classes.
- [ ] Integrar approvals.
- [ ] Plan hash binding.
- [ ] TTL curto.
- [ ] Non-renewable por defeito.
- [ ] Consume-once.
- [ ] Revoke-after-use.
- [ ] Signed evidence.

## 10. Recovery

- [ ] Snapshot automático.
- [ ] Cópia independente.
- [ ] Restore drill isolado.
- [ ] Runbook offline.
- [ ] Break-glass dry run sem exposição de material.

## 11. Assurance

- [ ] `RB-VAULT-001` implementado.
- [ ] Policy drift.
- [ ] Lease cleanup.
- [ ] PKI expiry.
- [ ] Snapshot freshness.
- [ ] Grafana dashboard.
- [ ] Negative tests recorrentes.

## 12. Production gate

- [ ] Todas as gates relevantes do roadmap PASS.
- [ ] Sem root persistente.
- [ ] Sem unmanaged high-risk secrets.
- [ ] Restore drill PASS.
- [ ] Audit PASS.
- [ ] NO_SECRET_TO_MODEL PASS.
- [ ] Tag/release criada.
