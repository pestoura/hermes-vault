"""Consumer-facing broker module.

Re-exports the provider-neutral broker so consumers depend on `src.capability`,
never on a Vault implementation.
"""
from src.capability_contract.broker import Capability, CapabilityBroker

__all__ = ["Capability", "CapabilityBroker"]
