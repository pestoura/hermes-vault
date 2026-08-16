from __future__ import annotations

from dataclasses import replace
from threading import RLock

from broker.model import CapabilityDescriptor


class CapabilityRegistry:
    def __init__(self) -> None:
        self._records: dict[str, CapabilityDescriptor] = {}
        self._request_handles: dict[str, str] = {}
        self._execution_handles: dict[str, set[str]] = {}
        self._lock = RLock()

    def register(self, descriptor: CapabilityDescriptor) -> None:
        with self._lock:
            if descriptor.handle in self._records:
                raise ValueError("duplicate capability handle")
            if descriptor.request_id in self._request_handles:
                raise ValueError("duplicate capability request_id")
            self._records[descriptor.handle] = descriptor
            self._request_handles[descriptor.request_id] = descriptor.handle
            self._execution_handles.setdefault(descriptor.execution_id, set()).add(descriptor.handle)

    def status(self, handle: str) -> CapabilityDescriptor:
        with self._lock:
            try:
                return self._records[handle]
            except KeyError as exc:
                raise KeyError("unknown capability handle") from exc

    def transition(self, handle: str, *, status: str, cleanup_status: str) -> CapabilityDescriptor:
        with self._lock:
            current = self.status(handle)
            updated = replace(current, status=status, cleanup_status=cleanup_status)
            self._records[handle] = updated
            return updated

    def active_for_execution(self, execution_id: str) -> list[CapabilityDescriptor]:
        with self._lock:
            handles = sorted(self._execution_handles.get(execution_id, set()))
            return [self._records[handle] for handle in handles if self._records[handle].status == "ACTIVE"]

    def snapshot(self) -> list[dict]:
        with self._lock:
            return [self._records[handle].to_public_dict() for handle in sorted(self._records)]
