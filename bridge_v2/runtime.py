from __future__ import annotations

from collections.abc import Callable
from typing import Any

from broker.evidence import build_broker_evidence
from broker.model import CapabilityRequest, PrivateCapability
from broker.redaction import sanitize
from broker.service import CredentialBroker, ExecutionCancelled

Executor = Callable[[dict[str, Any], PrivateCapability], Any]


class BridgeV2:
    def __init__(self, broker: CredentialBroker) -> None:
        self.broker = broker

    def _execute(self, call: dict[str, Any], executor: Executor, *, mode: str) -> dict[str, Any]:
        try:
            request_data = call.get("request") if isinstance(call, dict) else None
            request = CapabilityRequest.from_dict(request_data)
        except Exception:
            return {
                "status": "ERROR",
                "mode": mode,
                "error": {"category": "ValidationError", "message": "invalid capability request"},
            }

        handle: str | None = None
        public_result: Any = None
        public_error: dict[str, str] | None = None
        final_status = "ERROR"
        error_category: str | None = None

        try:
            with self.broker.session(request) as session:
                if session.descriptor is None or session.private_capability is None:
                    raise RuntimeError("capability session did not initialize")
                handle = session.descriptor.handle
                private = session.private_capability
                markers = [bytes(private.material)]
                try:
                    raw = executor(call, private)
                    public_result = sanitize(raw, secret_markers=markers)
                    final_status = "PASS"
                except Exception as exc:
                    error_category = type(exc).__name__
                    public_error = {
                        "category": error_category,
                        "message": sanitize(str(exc), secret_markers=markers),
                    }
                    final_status = "ERROR"
        except ExecutionCancelled:
            return {
                "status": "ERROR",
                "mode": mode,
                "error": {"category": "ExecutionCancelled", "message": "execution is cancelled"},
            }
        except Exception:
            return {
                "status": "ERROR",
                "mode": mode,
                "error": {"category": "BrokerError", "message": "capability execution failed"},
            }

        if handle is None:
            return {
                "status": "ERROR",
                "mode": mode,
                "error": {"category": "BrokerError", "message": "capability handle unavailable"},
            }
        descriptor = self.broker.status(handle)
        evidence = build_broker_evidence(
            request,
            descriptor,
            final_status=final_status,
            error_category=error_category,
        )
        response: dict[str, Any] = {
            "status": final_status,
            "mode": mode,
            "evidence": evidence,
        }
        if final_status == "PASS":
            response["result"] = public_result
        else:
            response["error"] = public_error or {"category": "ExecutionError", "message": "tool execution failed"}
        return response

    def execute_direct(self, call: dict[str, Any], executor: Executor) -> dict[str, Any]:
        return self._execute(call, executor, mode="direct")

    def execute_agent(self, call: dict[str, Any], agent_executor: Executor) -> dict[str, Any]:
        return self._execute(call, agent_executor, mode="agent")

    def execute_batch(self, calls: list[dict[str, Any]], executor: Executor) -> dict[str, Any]:
        results = [self.execute_direct(call, executor) for call in calls]
        statuses = [item.get("status") for item in results]
        if statuses and all(status == "PASS" for status in statuses):
            status = "PASS"
        elif statuses and all(status == "ERROR" for status in statuses):
            status = "ERROR"
        else:
            status = "PARTIAL"
        return {
            "status": status,
            "results": results,
        }
