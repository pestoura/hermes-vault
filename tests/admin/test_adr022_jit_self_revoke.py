from pathlib import Path

POLICY_DIR = Path("policies/admin")
JIT_POLICIES = [
    "vault-admin-policy.hcl",
    "vault-admin-auth.hcl",
    "vault-admin-token.hcl",
    "vault-admin-secrets-engine.hcl",
    "vault-admin-audit.hcl",
]


def test_each_jit_class_can_retire_its_own_token_without_default_policy():
    for name in JIT_POLICIES:
        text = (POLICY_DIR / name).read_text()
        assert 'path "auth/token/revoke-self"' in text, name
        block = text.split('path "auth/token/revoke-self"', 1)[1].split('}', 1)[0]
        assert '"update"' in block, name


def test_patch_does_not_add_general_introspection_or_renewal():
    for name in JIT_POLICIES:
        text = (POLICY_DIR / name).read_text()
        assert 'capabilities-self' not in text, name
        assert 'renew-self' not in text, name


def test_issuer_remains_single_purpose_and_gets_no_self_management():
    text = (POLICY_DIR / 'vault-admin-issuer.hcl').read_text()
    assert 'auth/token/create/hermes-vault-admin' in text
    assert 'auth/token/revoke-self' not in text
    assert 'lookup-self' not in text
    assert 'capabilities-self' not in text


def test_runbook_uses_real_operations_not_capabilities_self_for_jit_proof():
    text = Path('docs/runbooks/jit-admin-bootstrap.md').read_text()
    section = text.split('### 5. Prove JIT with root absent', 1)[1].split('### 6.', 1)[0]
    assert 'vaultc policy read vault-admin-policy' in section
    assert 'vaultc policy list' in section
    assert 'vaultc audit list' in section
    assert 'token capabilities' not in section
    assert 'vaultc token lookup' not in section
    assert 'JIT_JSON=' in section
    assert 'lease_duration' in section
    assert 'orphan' in section
    assert 'renewable' in section
    assert 'vaultc token revoke -self' in section
