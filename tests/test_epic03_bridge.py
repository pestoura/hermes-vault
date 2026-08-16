from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone

from broker.model import CapabilityRequest, PrivateCapability
from broker.registry import CapabilityRegistry
from broker.service import CredentialBroker
from bridge_v2.runtime import BridgeV2


class MultiProvider:
    def __init__(self):
        self.counter = 0
        self.revoked = []
        self.private_by_tool = {}

    def issue(self, req: CapabilityRequest) -> PrivateCapability:
        self.counter += 1
        marker = f"SECRET_FOR_{req.tool_identity}_{self.counter}".encode()
        cap = PrivateCapability(
            handle=f"cap-{self.counter:04d}",
            request_id=req.request_id,
            execution_id=req.execution_id,
            tool_identity=req.tool_identity,
            capability_type=req.capability_type,
            material=bytearray(marker),
            lease_id=f"lease-{self.counter:04d}",
            expires_at=datetime(2026, 8, 16, 18, 45, tzinfo=timezone.utc),
            cleanup_required=True,
        )
        self.private_by_tool[req.tool_identity] = cap
        return cap

    def revoke(self, capability: PrivateCapability) -> None:
        self.revoked.append(capability.handle)


def call(tool: str, index: int, **extra):
    data = {
        "mode": "direct",
        "payload": {"operation": "status"},
        "request": {
            "execution_id": "exec-batch",
            "plan_id": "plan-batch",
            "request_id": f"req-{index}",
            "tool_call_id": f"call-{index}",
            "principal": "hermes-controller",
            "tool_identity": tool,
            "action": f"{tool}.status",
            "resource_scope": f"scope/{tool}",
            "risk_class": "low",
            "requested_ttl_s": 120,
            "capability_type": "memory_only",
        },
    }
    data.update(extra)
    return data


class BridgeExecutionTests(unittest.TestCase):
    def setUp(self):
        self.provider = MultiProvider()
        self.broker = CredentialBroker(self.provider, CapabilityRegistry())
        self.bridge = BridgeV2(self.broker)

    def test_direct_path_secret_reaches_executor_but_not_public_result_or_evidence(self) -> None:
        observed = []
        def executor(call_data, private):
            secret = bytes(private.material).decode()
            observed.append(secret)
            return {"ok": True, "provider_message": f"echo={secret}", "token": secret}

        result = self.bridge.execute_direct(call("github-tool", 1), executor)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(observed), 1)
        encoded = json.dumps(result)
        self.assertNotIn(observed[0], encoded)
        self.assertNotIn('"token"', encoded.lower())
        self.assertEqual(result["evidence"]["schema"], "hermes-vault-broker-evidence/v1")
        self.assertEqual(result["evidence"]["final_status"], "PASS")
        self.assertEqual(result["evidence"]["cleanup_status"], "PASS")

    def test_agent_path_sanitizes_exception_text_and_cleans_capability(self) -> None:
        marker = []
        def agent_executor(call_data, private):
            secret = bytes(private.material).decode()
            marker.append(secret)
            raise RuntimeError(f"agent saw {secret}")

        result = self.bridge.execute_agent(call("outlook-tool", 2, mode="agent"), agent_executor)
        self.assertEqual(result["status"], "ERROR")
        encoded = json.dumps(result)
        self.assertNotIn(marker[0], encoded)
        self.assertEqual(result["error"]["category"], "RuntimeError")
        self.assertEqual(result["evidence"]["cleanup_status"], "PASS")

    def test_batch_uses_independent_capabilities_per_tool_and_sanitized_join(self) -> None:
        calls = [call("github-tool", 1), call("outlook-tool", 2), call("grafana-tool", 3)]
        seen = {}
        def executor(call_data, private):
            tool = call_data["request"]["tool_identity"]
            seen[tool] = (private.handle, id(private), bytes(private.material).decode())
            return {"tool": tool, "secret_echo": seen[tool][2]}

        result = self.bridge.execute_batch(calls, executor)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len({item[0] for item in seen.values()}), 3)
        self.assertEqual(len({item[1] for item in seen.values()}), 3)
        encoded = json.dumps(result)
        for _, _, secret in seen.values():
            self.assertNotIn(secret, encoded)
        self.assertEqual(len(self.provider.revoked), 3)

    def test_batch_partial_failure_continues_and_cleans_every_session(self) -> None:
        calls = [call("github-tool", 1), call("outlook-tool", 2), call("grafana-tool", 3)]
        secrets = []
        def executor(call_data, private):
            tool = call_data["request"]["tool_identity"]
            secret = bytes(private.material).decode()
            secrets.append(secret)
            if tool == "outlook-tool":
                raise ValueError(f"failed with {secret}")
            return {"tool": tool, "ok": True}

        result = self.bridge.execute_batch(calls, executor)
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual([item["status"] for item in result["results"]], ["PASS", "ERROR", "PASS"])
        self.assertEqual(len(self.provider.revoked), 3)
        encoded = json.dumps(result)
        for secret in secrets:
            self.assertNotIn(secret, encoded)

    def test_cancelled_execution_cannot_start_bridge_call(self) -> None:
        self.broker.cancel_execution("exec-batch")
        result = self.bridge.execute_direct(call("github-tool", 1), lambda *_: {"ok": True})
        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(result["error"]["category"], "ExecutionCancelled")
        self.assertEqual(self.provider.counter, 0)


if __name__ == "__main__":
    unittest.main()
