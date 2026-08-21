import os

import pytest


@pytest.fixture
def vault_addr():
    """Vault address sourced from the environment, defaulting to local dev listener.

    Later tasks use this fixture to point contract/isolation tests at a managed
    Vault instance without hardcoding endpoints in test code.
    """
    return os.environ.get("HERMES_VAULT_ADDR", "http://127.0.0.1:8200")
