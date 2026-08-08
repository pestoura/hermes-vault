# 13 — Decisões arquiteturais e de segurança

Este ficheiro regista decisões já tomadas para evitar que uma implementação futura reabra os mesmos temas sem contexto.

## ADR-001 — Vault como Trust Plane, não apenas secret store

**Decisão:** usar Vault para secrets, workload identity, PKI, Transit, leases e audit.

**Motivo:** o objetivo é aumentar autonomia do Hermes sem aumentar proporcionalmente a exposição de credenciais.

---

## ADR-002 — Root não pertence ao Hermes

**Decisão:** root/recovery ficam fora da cadeia operacional normal.

**Motivo:** um root persistente no Hermes transformaria compromisso da Bridge/agent numa perda total do Vault.

**Alternativa rejeitada:** guardar root em KV ou variável de ambiente do Hermes.

---

## ADR-003 — Administração Hermes através de JIT

**Decisão:** ChatGPT/Hermes pode administrar Vault por `hermes-vault-admin` temporário L3.

**Requisitos:** approval, plan binding, TTL curto, non-renewable por defeito, revogação e audit/evidence.

---

## ADR-004 — Identidade por tool/workload

**Decisão:** cada tool/MCP crítico recebe identidade e policy próprias.

**Motivo:** reduzir blast radius e permitir least privilege real.

---

## ADR-005 — Broker em vez de generic secret.read

**Decisão:** ChatGPT pede capabilities; não recebe endpoint genérico para ler secrets arbitrários.

**Motivo:** impedir que a interface MCP se transforme num exfiltration primitive.

---

## ADR-006 — Integrated Storage como baseline

**Decisão:** usar Vault Integrated Storage/Raft no baseline, salvo blocker técnico.

**Motivo:** evitar introduzir Consul sem necessidade.

---

## ADR-007 — Migração progressiva

**Decisão:** discovery → pilot → tool-by-tool migration.

**Alternativa rejeitada:** migração global de todos os `.env` num único cutover.

---

## ADR-008 — Dynamic secrets preferidos, não presumidos

**Decisão:** preferir dynamic credentials quando o provider/engine suporta de forma segura.

**Nota:** PATs, OAuth refresh tokens e API tokens externos podem continuar estáticos no KV e exigir adapters de rotação.

---

## ADR-009 — PKI para identidade interna

**Decisão:** introduzir certificados curtos/mTLS progressivamente entre componentes internos.

**Nota:** mTLS complementa, não substitui, autorização por policy.

---

## ADR-010 — Transit keys separadas por função

**Decisão:** execution signing, evidence signing, HMAC e field encryption usam chaves distintas.

**Motivo:** blast radius, rotação e policies independentes.

---

## ADR-011 — Audit obrigatório antes de migração relevante

**Decisão:** não migrar segredos críticos sem audit device operacional.

---

## ADR-012 — Restore test como gate de produção

**Decisão:** backup sem restore drill não é considerado capacidade de recuperação validada.

---

## ADR-013 — Community-first / feature-aware

**Decisão:** baseline não deve depender silenciosamente de features Enterprise/HCP.

**Motivo:** manter portabilidade e evitar custo/licenciamento não planeado.

Features Enterprise podem ser avaliadas quando requisitos concretos justificarem.

---

## ADR-014 — Git como baseline, nunca como secret store

**Decisão:** policies, config templates, runbooks e architecture podem ser versionados; secrets reais não.

---

## ADR-015 — Fail closed em operações críticas

**Decisão:** se policy, approval, Vault, signing ou identity validation necessária falhar, a operação não deve degradar automaticamente para um secret local mais permissivo.

Fallback só existe se explicitamente desenhado e testado.

---

## ADR-016 — Self-healing limitado por risco

**Decisão:** self-healing autónomo apenas para ações reversíveis e de baixo risco. Admin Vault, root/recovery, CA replacement e mass revocation exigem gates específicas.

---

## ADR-017 — Secret zero precisa de desenho explícito

**Decisão:** a credencial inicial usada por cada workload para autenticar no Vault deve ser tratada como problema de bootstrap próprio.

AppRole SecretID, certificado, JWT ou outro bootstrap material não pode ser simplesmente movido para outro `.env` e considerado resolvido.
