# Task A3 — Fix Round 1/5 — Scratch Report

## Objective
Fix reviewer Important finding: `CapabilityRequest.model_dump()` must emit a
provider-neutral wire value string for `capability_type` instead of a Python
Enum object, while the model attribute stays strongly typed as `CapabilityType`.
Add a focused failing test (also covers Minor M1: positive enum coverage).
Smallest Pydantic v2-native solution (field serializer), no global weakening of
validation. No secret-value scanning (ruled out of scope: H1/G2).

## Files changed
- src/capability_contract/schema.py  (fix)
- tests/contract/test_capability_contract.py  (added failing test)

## Fix
Added a scoped `@field_serializer("capability_type")` to `CapabilityRequest`
that returns `value.value` (str) when present, else `None`. This is the
minimal Pydantic v2-native change: it only affects serialization of this one
field and does not alter `model_config`, validation, or the strongly typed
attribute.

## RED (before fix)
```
tests/contract/test_capability_contract.py::test_capability_type_serializes_to_wire_string
E  AssertionError: assert <enum 'CapabilityType'> is str
1 failed, 2 passed
```

## GREEN (after fix)
A3 tests:
```
tests/contract/test_capability_contract.py  3 passed
```
Full suite:
```
10 passed in 0.18s
```
No warnings (`-W error` clean). Collection: 10 tests across contract /
policy_lint / scaffold.

## Self-review
- Typed attribute preserved: `isinstance(r.capability_type, CapabilityType)` true
  after construction and after round-trip parse from wire string.
- Wire value emitted: `type(model_dump()["capability_type"]) is str` and equals
  `CapabilityType.ephemeral_token.value`.
- `model_dump(mode="json")` also emits plain string.
- `None` capability_type serializes to `None` (no value coercion).
- Strong validation untouched: `extra="forbid"` and field constraints intact.
- No secret-material fields introduced; secret scanning explicitly out of scope.

## Concerns
- The field serializer applies to every serialization path (model_dump /
  model_dump_json / response/transport serialization). That is intended: any
  provider receiving the contract gets a wire string, not an Enum. No provider
  code depends on receiving the Enum object (none in repo).
- Serializer is field-scoped, not global, so other `str,Enum` usage elsewhere
  is unaffected.
- `capability_type` default `None` remains valid and serializes to `null`.

## Commit
- message: `fix(contract): serialize capability type as wire value`
- only A3 fix files staged.
