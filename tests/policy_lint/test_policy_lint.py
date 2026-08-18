from src.policy_lint.linter import lint_policy_text


def test_wildcard_rejected():
    bad = 'path "secret/*" { capabilities = ["read"] }'
    issues = lint_policy_text(bad, identity="hsl-signer")
    assert any("wildcard" in i.lower() for i in issues)


def test_sudo_rejected_for_normal_identity():
    bad = 'path "auth/*" { capabilities = ["sudo", "update"] }'
    issues = lint_policy_text(bad, identity="hsl-signer")
    assert any("sudo" in i.lower() for i in issues)


def test_exact_path_accepted():
    good = 'path "transit/sign/hsl-transit/hsl-signing" { capabilities = ["update"] }'
    assert lint_policy_text(good, identity="hsl-signer") == []
