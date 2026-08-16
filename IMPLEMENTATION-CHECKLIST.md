# Hermes Vault — Implementation Checklist

Utilizar esta checklist quando a implementação for iniciada.

## 0. Pre-flight

- [x] Ler README e `docs/12-implementation-roadmap.md`.
- [x] Confirmar versão/edição Vault pretendida.
- [x] Confirmar que nenhum secret real será colocado no Git.
- [x] Criar branch de implementação.
- [ ] Registar execution/plan IDs se executado via Hermes.

## 1. Discovery

- [ ] Inventariar consumidores e secret references.
- [x] Preparar `templates/secret-inventory.yaml` sem valores secretos.
- [x] Implementar classificação static/dynamic/PKI/Transit/bootstrap.
- [ ] Identificar owners e rollback a partir de evidência live.
- [ ] Mapear tool identities a partir de evidência live.

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

## Phase 0 repository implementation status — 2026-08-16

- [x] Read-only discovery collector contract implemented.
- [x] Secret-reference parser emits names/locations only; synthetic leakage tests included.
- [x] Host, storage, systemd, Docker and listener collectors implemented with bounded allowlists.
- [x] TLS public-certificate metadata and Vault prerequisite observation implemented.
- [x] Versioned report and fail-closed `DISCOVERY_COMPLETE` evaluator implemented.
- [x] Repository CI contract prepared.
- [ ] Live Jarvas discovery executed and validated.
- [ ] `DISCOVERY_COMPLETE` accepted from live evidence.
- [ ] `NO_SECRET_IN_REPO` accepted by repository gate/review.
- [ ] `TARGET_ARCHITECTURE_APPROVED` recorded by its authority.
- [ ] `RECOVERY_DESIGN_DEFINED` accepted by its authority.

## EPIC-01 repository implementation status — 2026-08-16

- [x] Immutable HSL LAB_L1 deployment provenance pinned by exact commit and blob identities.
- [x] Audit named-volume overlay prepared without host bind mounts.
- [x] Idempotent file audit device configuration contract prepared.
- [x] Read-only Raft snapshot backup policy prepared.
- [x] Bounded single-use backup AppRole bootstrap operations prepared.
- [x] Atomic manual snapshot save/inspect/SHA-256 workflow prepared.
- [x] Isolated restore-drill plan/preflight prepared; destructive restore remains HITL-only.
- [ ] HSL baseline actually staged on Jarvas.
- [ ] Vault initialized and unsealed live.
- [ ] Audit device enabled and verified live.
- [ ] Snapshot saved, inspected and independently copied live.
- [ ] Initial root revoked live.
- [ ] Isolated restore drill executed and accepted.

## EPIC-02 repository implementation status — 2026-08-16

- [x] AppRole identity contract prepared for `hermes-runtime`, `hermes-controller`, `jarvas-operations` and `github-tool`.
- [x] Role TTL/SecretID/wrapping bounds validated in repository tests.
- [x] Exact minimal policies prepared; runtime/controller/operations have no direct KV access.
- [x] `github-tool` policy restricted to exact GitHub runtime data/metadata paths.
- [x] Policy linter prepared with wildcard, sudo, admin-path and cross-tool protections.
- [x] KV v2 `secret/` mount bootstrap/status contract prepared without secret writes.
- [x] Positive/negative capability matrix prepared for all four identities.
- [x] Reference-only KV pilot handoff and migration/rollback runbook prepared.
- [ ] AppRoles/policies configured live on Jarvas Vault.
- [ ] `AUTH_PASS` accepted from live evidence.
- [ ] `LEAST_PRIVILEGE_PASS` and `NEGATIVE_TEST_PASS` accepted from live role sessions.
- [ ] Real low-risk pilot selected from live discovery with owner/rollback evidence.
- [ ] Pilot credential migrated/cut over live.
- [ ] Legacy credential rotated/revoked and removed live.
- [ ] Restart/reboot acceptance and secret scan completed live.

## EPIC-03 repository implementation status — 2026-08-16

- [x] Provider-neutral capability request/descriptor/private-capability model implemented.
- [x] Mandatory correlation identifiers and bounded TTL validation implemented.
- [x] Secret-free lifecycle registry implemented with duplicate request/handle protection.
- [x] Request/status/revoke and execution cancellation lifecycle implemented.
- [x] Private capability session implemented with cleanup on success and exception.
- [x] Best-effort application-level bytearray zeroization implemented and documented with limitations.
- [x] Recursive result redaction and synthetic NO_SECRET_TO_MODEL contracts implemented.
- [x] Direct-tool and agent execution paths implemented against provider-neutral ports.
- [x] Multi-tool batch contract implemented with independent capability objects and cleanup on partial failure.
- [x] Sanitized broker evidence schema `hermes-vault-broker-evidence/v1` implemented.
- [x] Credential Broker / Bridge V2 live integration runbook prepared.
- [ ] Real Vault-backed `CapabilityProvider` integrated on Jarvas.
- [ ] Hermes MCP Bridge V2 wired to the Broker live.
- [ ] `BROKER_ACCEPTANCE_PASS` accepted from live evidence.
- [ ] `NO_SECRET_TO_MODEL` accepted against live provider-shaped flows.
- [ ] `LEASE_CLEANUP_PASS` and `CANCEL_CLEANUP_PASS` accepted live.
- [ ] `BATCH_EXECUTION_PASS` and `SEPARATE_CAPABILITIES_PASS` accepted live.
- [ ] `NO_CROSS_TOOL_SECRET_ACCESS` and `SANITIZED_RESULT_PASS` accepted live.
