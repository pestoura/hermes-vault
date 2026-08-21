"""Consumer-facing entrypoint for the provider-neutral capability contract.

Consumers import from `src.capability` and depend on the contract only — never on a
Vault implementation (#18 adapter deferred).
"""
from .broker import Capability, CapabilityBroker

__all__ = ["Capability", "CapabilityBroker"]
