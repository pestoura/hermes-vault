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

---

## ADR-018 — Continuidade criptográfica HSL por verify-only

**Decisão:** a chave histórica HSL `hermes-lab-l1-signer`, por ser não exportável, permanece no deployment legado exclusivamente em modo **verify-only** durante a janela de continuidade. Depois do cutover não são produzidas novas assinaturas com essa chave.

**Regra de integridade:** evidência histórica não é sujeita a bulk re-sign/re-signing para simular continuidade criptográfica. A assinatura original e a respetiva cadeia de verificação são preservadas enquanto existir obrigação de retenção/verificação.

**Motivo:** manter verificabilidade e proveniência histórica sem tentar exportar material não exportável nem substituir assinaturas originais por novas assinaturas semanticamente diferentes.

**Saída:** o componente legado pode ser retirado apenas quando a política de retenção/continuidade permitir abandonar a verificação histórica ou existir mecanismo canónico equivalente aprovado.

---

## ADR-019 — Security plane Docker privado, sem exposição LAN

**Decisão:** o Vault partilhado integra a rede Docker privada `hermes-security-plane`, declarada com `internal: true`, e usa o alias DNS interno `hermes-vault` para comunicação container-to-container.

**Publicação no host:** mantém-se exclusivamente `127.0.0.1:8200:8200` para operação local. Não é permitido publicar a API Vault em `0.0.0.0`, endereço LAN, Internet, host networking ou ingress/reverse proxy no MVP.

**Consumo:** consumidores autorizados juntam-se à rede `hermes-security-plane` no respetivo onboarding e usam TLS para `hermes-vault:8200`. A adesão de um consumidor não transfere ownership da rede/serviço para esse consumidor.

**Motivo:** permitir conectividade entre stacks Docker independentes no Jarvas sem aumentar a superfície de exposição do serviço.

---

## ADR-019A — Topologia dual-network para administração local

**Contexto:** a verificação live pré-init no HermesJarvas confirmou que, com o Vault ligado apenas à rede Docker `hermes-security-plane` marcada `internal: true`, o Docker preserva a declaração `127.0.0.1:8200:8200` no HostConfig mas não materializa conectividade útil no loopback do host. O listener TLS dentro do contentor continuava operacional e o problema estava na fronteira de rede.

**Decisão:** o Vault liga-se simultaneamente a duas redes com funções estritamente separadas:

- `hermes-security-plane`: continua `internal: true`, mantém o alias `hermes-vault` e é a única rede permitida para consumidores;
- `hermes-vault-admin`: bridge administrativa dedicada, não interna apenas para permitir a publicação local `127.0.0.1:8200:8200`; não recebe o alias de consumidor, não é usada por workloads e tem IP masquerade desativado.

**Exposição:** continua proibida qualquer publicação em `0.0.0.0`, endereço LAN, Internet, ingress, reverse proxy ou host networking. A porta Raft/cluster `8201` nunca é publicada no host.

**Limite de confiança:** `hermes-vault-admin` não é uma rede de egress nem uma nova security plane. A ausência de masquerade reduz a capacidade de saída normal, mas não substitui controlos de host/firewall; consumidores não devem aderir a esta rede.

**Motivo:** preservar simultaneamente o isolamento forte da rede de consumidores e o endpoint administrativo local definido na ADR-019, adaptando o mecanismo ao comportamento Docker observado no Jarvas.

**Estado:** **Decisão — APROVADA em 2026-08-21**, após validação runtime pré-init.

---

## ADR-020 — Parallel-run controlado para cutover HSL

**Decisão:** a migração HSL usa **parallel-run controlado**. Enquanto o novo shared Vault está em aceitação, o caminho legado mantém o estado pré-cutover. Depois de todas as gates live obrigatórias passarem, o shared Vault torna-se a única autoridade para assinar **new evidence / nova evidência**, e o Vault HSL legado passa a **verify-only**.

**Gate de cutover:** exige, no mínimo, health/unseal operacional, `AUDIT_PASS`, `RESTORE_DRILL_PASS`, isolamento/negative-capability HSL, conectividade TLS, sign/verify do novo signer e verificação de evidência histórica pelo caminho legado.

**Rollback:** antes do cutover, regressar ao legado não altera autoridade. Depois do cutover não se volta automaticamente a assinar com a chave histórica; qualquer reversão de autoridade de signing é uma nova decisão owner-gated.

**Motivo:** reduzir risco de migração e preservar rollback sem criar duas autoridades concorrentes para novas assinaturas.

---

## ADR-021 — Shamir 3/2 com custódia independente out-of-band

**Decisão:** manter **Shamir 3/2**: três shares, threshold dois. As três shares ficam sob **three independent** custódias/localizações out-of-band, fora de GitHub, Hermes, Jarvas e de qualquer storage que o próprio Vault proteja.

**Proibição de metadados sensíveis:** a concrete location/localização concreta de cada share, identificadores de suporte, passwords, envelopes, chaves de cifragem ou outros locators de recovery não são registados neste repositório, no Context Core, em logs ou em estado operacional do Hermes/Jarvas.

**Operação:** criação, distribuição, consulta, utilização e rotação das shares são exclusivamente HITL. O repositório pode documentar responsabilidades, quorum e procedimento, nunca o material nem a sua localização concreta.

**Motivo:** evitar que comprometimento do host/automação/repositório forneça simultaneamente storage Vault e material necessário para o desbloquear.

---

## ADR-022 — Administração JIT por certificado após bootstrap audit-first

**Decisão:** substituir o initial root token por uma cadeia administrativa JIT baseada em certificado cliente. A ordem canónica de bootstrap é: `audit` → policies administrativas → `auth/cert` → identidade `vault-admin-issuer` → token role `hermes-vault-admin` → prova independente sem root → revogação do initial root token.

**Identidade de entrada:** o certificado cliente do operador é self-signed/dedicado a esta função e é registado apenas pelo seu certificado público. A respetiva private key é segredo operator-only, nunca é versionada, lida por automação, guardada no Hermes/Context Core, nem enviada para prompts/logs.

**Issuer:** o login por certificado recebe apenas a policy `vault-admin-issuer`. Essa policy pode exclusivamente efetuar `update` em `auth/token/create/hermes-vault-admin`; não recebe capacidades administrativas diretas.

**JIT admin:** a token role `hermes-vault-admin` emite apenas policies administrativas explicitamente permitidas, com `orphan=true`, `renewable=false` (**non-renewable**), sem `default` policy e `token_explicit_max_ttl=10m`. O pedido deve selecionar apenas as classes necessárias à operação.

**Audit-first:** o audit device é ativado e validado antes da instalação/uso da cadeia JIT. Exceções só existem em recovery/break-glass explicitamente autorizado.

**Root:** o initial root token permanece exclusivamente out-of-band durante o bootstrap e é revogado apenas depois de uma prova independente demonstrar: login por certificado, emissão de JIT token, capability positiva esperada, negative capability fora do scope e revogação do JIT token.

**Motivo:** remover root da operação normal sem substituir um segredo privilegiado permanente por outro, preservar least privilege e produzir trilho de auditoria desde o início da administração pós-bootstrap.
