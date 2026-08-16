from __future__ import annotations

from typing import Protocol

from broker.model import CapabilityRequest, PrivateCapability


class CapabilityProvider(Protocol):
    def issue(self, request: CapabilityRequest) -> PrivateCapability: ...

    def revoke(self, capability: PrivateCapability) -> None: ...
