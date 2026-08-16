from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone

from broker.evidence import build_broker_evidence
from broker.model import CapabilityRequest, CapabilityDescriptor, PrivateCapability
from broker.redaction import sanitize
from broker.registry import CapabilityRegistry
from broker.service import CredentialBroker

SECRET = b"SYNTHETIC_PROVIDER_SECRET_EPIC03"


def request(**overrides):
    data = {
        "execution_id": "exec-001",
        "plan_id": "plan-001",
        "request_id": "req-001",
        "tool_call_id": "call-001",
        "principal": "hermes-controller",
        "tool_identity": "github-tool",
        "action": "github.ci.status",
        "resource_scope": "pestoura/project",
        "risk_class": "medium",
        "requested_ttl_s": 300,
        "capability_type": "wrapped_secret",
    }
    data.update(overrides)
    return CapabilityRequest.from_dict(data)


class FakeProvider:
    def __init__(self):
        self.issued = []
        self.revoked = []
        self.counter = 0

    def issue(self, req: CapabilityRequest) -> PrivateCapability:
        self.counter += 1
        private = PrivateCapability(
            handle=f"cap-{self.counter:04d}",
            request_id=req.request_id,
            execution_id=req.execution_id,
            tool_identity=req.tool_identity,
            capability_type=req.capability_type,
            material=bytearray(SECRET + f"-{self.counter}".encode()),
            lease_id=f"lease-{self.counter:04d}",
            expires_at=datetime(2026, 8, 16, 18, 30, tzinfo=timezone.utc),
            cleanup_required=True,
        )
        self.issued.append(private)
        return private

    def revoke(self, capability: PrivateCapability) -> None:
        self.revoked.append(capability.handle)


class ModelAndRedactionTests(unittest.TestCase):
    def test_request_requires_correlation_and_bounded_ttl(self) -> None:
        req = request()
        self.assertEqual(req.request_id, "req-001")
        self.assertEqual(req.requested_ttl_s, 300)
        with self.assertRaises(ValueError):
            request(request_id="")
        with self.assertRaises(ValueError):
            request(requested_ttl_s=1801)
        with self.assertRaises(ValueError):
            request(capability_type="root_token")

    def test_descriptor_public_dict_is_stable_and_secret_free(self) -> None:
        descriptor = CapabilityDescriptor(
            handle="cap-1",
            request_id="req-1",
            execution_id="exec-1",
            tool_identity="github-tool",
            capability_type="wrapped_secret",
            lease_id="lease-1",
            expires_at="2026-08-16T18:30:00Z",
            cleanup_required=True,
            status="ACTIVE",
            cleanup_status="PENDING",
        )
        public = descriptor.to_public_dict()
        self.assertEqual(public["handle"], "cap-1")
        self.assertNotIn("material", public)
        self.assertNotIn("token", json.dumps(public).lower())

    def test_private_capability_is_not_json_serializable_and_zeroizes(self) -> None:
        private = PrivateCapability(
            handle="cap-x",
            request_id="req-x",
            execution_id="exec-x",
            tool_identity="github-tool",
            capability_type="memory_only",
            material=bytearray(b"secret-bytes"),
            lease_id=None,
            expires_at=None,
            cleanup_required=True,
        )
        with self.assertRaises(TypeError):
            json.dumps(private)
        private.zeroize()
        self.assertTrue(private.zeroized)
        self.assertTrue(all(value == 0 for value in private.material))

    def test_recursive_sanitizer_redacts_sensitive_keys_bearer_and_known_marker(self) -> None:
        value = {
            "request_id": "req-1",
            "token": "abc123",
            "nested": [
                {"authorization": "Bearer abc.def.ghi"},
                f"provider echoed {SECRET.decode()} here",
            ],
        }
        safe = sanitize(value, secret_markers=[SECRET])
        encoded = json.dumps(safe)
        self.assertIn("req-1", encoded)
        for forbidden in ("abc123", "abc.def.ghi", SECRET.decode()):
            self.assertNotIn(forbidden, encoded)
        self.assertIn("[REDACTED]", encoded)

    def test_evidence_schema_is_safe_and_contains_no_secret_fields_or_markers(self) -> None:
        req = request()
        descriptor = CapabilityDescriptor(
            handle="cap-safe",
            request_id=req.request_id,
            execution_id=req.execution_id,
            tool_identity=req.tool_identity,
            capability_type=req.capability_type,
            lease_id="lease-safe",
            expires_at="2026-08-16T18:30:00Z",
            cleanup_required=True,
            status="REVOKED",
            cleanup_status="PASS",
        )
        evidence = build_broker_evidence(req, descriptor, final_status="PASS")
        self.assertEqual(evidence["schema"], "hermes-vault-broker-evidence/v1")
        encoded = json.dumps(evidence)
        for forbidden in (
            SECRET.decode(),
            '"token"',
            '"secret"',
            '"password"',
            '"private_key"',
            '"authorization"',
            '"wrapped_payload"',
            '"recovery"',
            '"unseal"',
        ):
            self.assertNotIn(forbidden, encoded.lower() if forbidden.startswith('"') else encoded)
        self.assertEqual(evidence["cleanup_status"], "PASS")


class RegistryAndBrokerTests(unittest.TestCase):
    def setUp(self):
        self.provider = FakeProvider()
        self.registry = CapabilityRegistry()
        self.broker = CredentialBroker(self.provider, self.registry)

    def test_registry_snapshot_never_contains_private_material(self) -> None:
        descriptor = self.broker.request(request())
        snapshot = self.registry.snapshot()
        encoded = json.dumps(snapshot)
        self.assertIn(descriptor.handle, encoded)
        self.assertNotIn(SECRET.decode(), encoded)
        self.assertNotIn("material", encoded.lower())

    def test_registry_rejects_duplicate_request_and_handle(self) -> None:
        self.broker.request(request())
        with self.assertRaises(ValueError):
            self.broker.request(request())

        other = request(request_id="req-002", tool_call_id="call-002")
        self.provider.counter = 0
        with self.assertRaises(ValueError):
            self.broker.request(other)

    def test_request_status_revoke_zeroizes_and_is_idempotent(self) -> None:
        descriptor = self.broker.request(request())
        self.assertEqual(self.broker.status(descriptor.handle).status, "ACTIVE")
        private = self.provider.issued[-1]
        revoked = self.broker.revoke(descriptor.handle, "completed")
        self.assertEqual(revoked.status, "REVOKED")
        self.assertEqual(revoked.cleanup_status, "PASS")
        self.assertTrue(private.zeroized)
        self.assertEqual(self.provider.revoked, [descriptor.handle])
        again = self.broker.revoke(descriptor.handle, "completed-again")
        self.assertEqual(again.status, "REVOKED")
        self.assertEqual(self.provider.revoked, [descriptor.handle])

    def test_cancel_execution_revokes_only_target_execution_and_blocks_new_issue(self) -> None:
        first = self.broker.request(request())
        second = self.broker.request(request(request_id="req-002", tool_call_id="call-002", tool_identity="outlook-tool"))
        other = self.broker.request(request(execution_id="exec-999", plan_id="plan-999", request_id="req-999", tool_call_id="call-999"))
        cancelled = self.broker.cancel_execution("exec-001")
        self.assertEqual({item.handle for item in cancelled}, {first.handle, second.handle})
        self.assertEqual(self.broker.status(other.handle).status, "ACTIVE")
        with self.assertRaises(RuntimeError):
            self.broker.request(request(request_id="req-003", tool_call_id="call-003"))
        self.assertEqual(self.broker.status(other.handle).status, "ACTIVE")

    def test_session_exposes_private_only_inside_context_and_cleans_on_exception(self) -> None:
        private_ref = None
        with self.assertRaisesRegex(RuntimeError, "tool failed"):
            with self.broker.session(request()) as session:
                private_ref = session.private_capability
                self.assertIn(SECRET, bytes(private_ref.material))
                self.assertEqual(session.descriptor.status, "ACTIVE")
                raise RuntimeError("tool failed")
        assert private_ref is not None
        self.assertTrue(private_ref.zeroized)
        final = self.broker.status(private_ref.handle)
        self.assertEqual(final.status, "REVOKED")
        self.assertEqual(final.cleanup_status, "PASS")


if __name__ == "__main__":
    unittest.main()
