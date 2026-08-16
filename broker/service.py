from __future__ import annotations

from broker.model import CapabilityDescriptor, CapabilityRequest, PrivateCapability
from broker.ports import CapabilityProvider
from broker.registry import CapabilityRegistry
from broker.session import CapabilitySession


class ExecutionCancelled(RuntimeError):
    pass


class CredentialBroker:
    def __init__(self, provider: CapabilityProvider, registry: CapabilityRegistry | None = None) -> None:
        self.provider = provider
        self.registry = registry or CapabilityRegistry()
        self._private: dict[str, PrivateCapability] = {}
        self._cancelled_executions: set[str] = set()

    def _validate_private(self, request: CapabilityRequest, private: PrivateCapability) -> None:
        if private.request_id != request.request_id:
            raise ValueError("provider request_id mismatch")
        if private.execution_id != request.execution_id:
            raise ValueError("provider execution_id mismatch")
        if private.tool_identity != request.tool_identity:
            raise ValueError("provider tool_identity mismatch")
        if private.capability_type != request.capability_type:
            raise ValueError("provider capability_type mismatch")

    def _issue(self, request: CapabilityRequest) -> tuple[CapabilityDescriptor, PrivateCapability]:
        if request.execution_id in self._cancelled_executions:
            raise ExecutionCancelled("execution is cancelled")
        private = self.provider.issue(request)
        try:
            self._validate_private(request, private)
            descriptor = private.descriptor()
            self.registry.register(descriptor)
        except Exception:
            try:
                self.provider.revoke(private)
            finally:
                private.zeroize()
            raise
        self._private[descriptor.handle] = private
        return descriptor, private

    def request(self, request: CapabilityRequest) -> CapabilityDescriptor:
        descriptor, _ = self._issue(request)
        return descriptor

    def _issue_for_session(self, request: CapabilityRequest) -> tuple[CapabilityDescriptor, PrivateCapability]:
        return self._issue(request)

    def status(self, handle: str) -> CapabilityDescriptor:
        return self.registry.status(handle)

    def revoke(self, handle: str, reason: str) -> CapabilityDescriptor:
        del reason  # reason is intentionally not persisted in the secret-free registry.
        current = self.registry.status(handle)
        if current.status != "ACTIVE":
            return current
        private = self._private.pop(handle, None)
        if private is None:
            return self.registry.transition(handle, status="REVOKED", cleanup_status="PASS")
        try:
            if private.cleanup_required:
                self.provider.revoke(private)
            private.zeroize()
        except Exception as exc:
            private.zeroize()
            self.registry.transition(handle, status="REVOKED", cleanup_status="ERROR")
            raise RuntimeError("capability cleanup failed") from exc
        return self.registry.transition(handle, status="REVOKED", cleanup_status="PASS")

    def cancel_execution(self, execution_id: str) -> list[CapabilityDescriptor]:
        if not isinstance(execution_id, str) or not execution_id:
            raise ValueError("execution_id must be non-empty")
        self._cancelled_executions.add(execution_id)
        results: list[CapabilityDescriptor] = []
        for descriptor in self.registry.active_for_execution(execution_id):
            results.append(self.revoke(descriptor.handle, "execution_cancelled"))
        return results

    def session(self, request: CapabilityRequest) -> CapabilitySession:
        return CapabilitySession(self, request)
