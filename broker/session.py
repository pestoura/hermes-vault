from __future__ import annotations

from typing import TYPE_CHECKING

from broker.model import CapabilityDescriptor, CapabilityRequest, PrivateCapability

if TYPE_CHECKING:
    from broker.service import CredentialBroker


class CapabilitySession:
    def __init__(self, broker: "CredentialBroker", request: CapabilityRequest) -> None:
        self._broker = broker
        self._request = request
        self.descriptor: CapabilityDescriptor | None = None
        self.private_capability: PrivateCapability | None = None

    def __enter__(self) -> "CapabilitySession":
        descriptor, private = self._broker._issue_for_session(self._request)
        self.descriptor = descriptor
        self.private_capability = private
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        if self.descriptor is not None:
            reason = "exception" if exc_type is not None else "completed"
            self._broker.revoke(self.descriptor.handle, reason)
        return False
