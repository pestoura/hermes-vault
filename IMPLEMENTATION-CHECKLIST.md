# Hermes Vault — Implementation Checklist

Esta checklist representa o estado real verificado do projeto. Um item só é marcado `[x]` quando existe implementação/evidência suficiente; `NOT_RUN` nunca é tratado como concluído.

## 0. Pre-flight e source of truth

- [x] Definir arquitetura e trust boundaries.
- [x] Fixar versão/edição Vault Community.
- [x] Garantir secret-zero / nenhum secret real no Git.
- [x] Definir modelo Shamir 3/2 e custódia out-of-band.
- [x] Definir recuperação e restore acceptance.
- [x] Definir topologia de redes e endpoint administrativo.

## 1. Vault baseline

- [x] Instalar versão fixada.
- [x] Configurar TLS.
- [x] Configurar Integrated Storage.
- [x] Inicializar Vault de forma controlada.
- [x] Proteger recovery/unseal material fora do Hermes.
- [x] Configurar audit device.
- [x] Configurar snapshots.
- [x] Criar administração JIT por certificado.
- [x] Revogar initial root.
- [x] Configurar `restart: unless-stopped`.
- [x] Configurar readiness timer secret-free.

## 2. Recovery e backup

- [x] Snapshot automático.
- [x] Snapshot cifrado com checksum independente.
- [x] Retenção local configurada.
- [ ] Cópia independente/off-host do snapshot.
- [x] Restore drill isolado.
- [x] Acceptance positiva/negativa pós-restore.
- [x] Teardown / zero residue do restore.
- [x] Runbook offline-capable documentado.
- [ ] RTO/RPO operacional formalmente medido e aceite.

## 3. Administração e identidade

- [x] Auth method por certificado para JIT admin.
- [x] Policy classes administrativas separadas.
- [x] TTL curto / non-renewable / no-default-policy.
- [x] Initial root retirado da operação normal.
- [ ] Revalidar `auth/token/revoke-self` no runtime para JIT administrativo.
- [x] Criar AppRole `vault-backup` mínimo.
- [x] Provar self-revoke do token `vault-backup`.
- [ ] Criar primeira identidade de consumidor HSL.
- [ ] Executar positive/negative capability test do HSL.

## 4. HSL first consumer

- [ ] Ativar/validar `hsl-transit/` no shared Vault.
- [ ] Criar/validar key `hsl-signing`.
- [ ] Aplicar policy mínima `hsl-signer`.
- [ ] Garantir `approle/` ativo.
- [ ] Criar role `hsl-signer`.
- [ ] Entregar RoleID/SecretID por boundary HITL apropriado.
- [ ] Provar assinatura no shared Vault.
- [ ] Provar deny fora do scope.
- [ ] Manter legacy signer verify-only durante transição.
- [ ] Concluir consumer cutover.
- [ ] Promover `UNSEALED_READY` apenas após acceptance.

## 5. Credential Broker / Hermes integration

- [x] Definir capability request contract repository-side.
- [x] Definir redaction/secret-zero invariants repository-side.
- [ ] Implementar Credential Broker live.
- [ ] Integrar request/status/revoke end-to-end.
- [ ] Implementar wrapped/memory-only delivery onde aplicável.
- [ ] Provar NO SECRET TO MODEL num consumer real.
- [ ] Integrar Hermes Bridge V2 em produção.

## 6. Transit / PKI / future capabilities

- [ ] HSL Transit live consumer acceptance.
- [ ] Evidence signing live consumer.
- [ ] HMAC use case live.
- [ ] Transit rotation exercise.
- [ ] Decidir root/intermediate PKI design.
- [ ] Criar PKI roles.
- [ ] Emitir certificado piloto.
- [ ] Automatizar renewal.
- [ ] Ativar mTLS num caminho interno.

## 7. Assurance

- [x] Readiness operacional secret-free ativo.
- [x] Snapshot freshness operacional através de timer diário.
- [x] Restore drill real executado.
- [x] Secret scan e gates CI ativos.
- [ ] Policy drift live periódico.
- [ ] Lease cleanup periódico.
- [ ] PKI expiry monitoring.
- [ ] Grafana dashboard dedicado ao Vault.
- [ ] Negative tests recorrentes por consumer.

## 8. Final production/consumer gate

- [x] Vault core runtime operacional.
- [x] Sem root persistente em operação normal.
- [x] Audit PASS.
- [x] Restore drill PASS.
- [x] Scheduled snapshot PASS.
- [ ] `JIT_SELF_REVOKE_REVALIDATION` PASS.
- [ ] `FIRST_CONSUMER_BOOTSTRAP` PASS.
- [ ] `UNSEALED_READY` promovido com evidência.
- [ ] Tag/release de consumer-ready criada.
