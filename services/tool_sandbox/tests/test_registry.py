"""Unit tests for ToolRegistry.

We construct a tools/ directory layout in a tmp_path, point the registry
at it, and exercise:
  - discovery (skips invalid, loads valid)
  - ACL enforcement
  - input/output schema validation
  - signature verification gating

We use `AllowAllVerifier` for the happy-path tests and `CosignVerifier`
+ `sign_blob_for_testing` for the signature-gating tests, so no cosign
binary is required.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import pytest
import yaml

from services.tool_sandbox.executor import ExecutionResult, WasmExecutor
from services.tool_sandbox.registry import (
    SchemaValidationError,
    ToolNotAllowedError,
    ToolRegistry,
    UnknownToolError,
)
from services.tool_sandbox.verifier import (
    AllowAllVerifier,
    CosignVerifier,
    SignatureVerificationError,
    generate_test_keypair,
    sign_blob_for_testing,
)

pytestmark = [pytest.mark.unit]


# --- helpers ------------------------------------------------------------

class FakeExecutor(WasmExecutor):
    """Returns a canned output without actually executing WASM."""

    def __init__(self, canned: dict[str, Any]) -> None:
        super().__init__()
        self.canned = canned
        self.calls: list[tuple[str, dict]] = []

    async def execute(self, wasm_bytes, input_payload, *, limits=None, tool_name="<anon>"):
        self.calls.append((tool_name, dict(input_payload)))
        return ExecutionResult(output=dict(self.canned), wall_seconds=0.01)


def _make_tool(
    tools_root: Path,
    name: str,
    *,
    wasm_bytes: bytes = b"\0asm\x01\x00\x00\x00",  # WASM magic; bytes are fine for tests
    signature_b64: str | None = None,
    allowed_agents: list[str] | None = None,
    input_schema: dict | None = None,
    output_schema: dict | None = None,
) -> Path:
    tool_dir = tools_root / name
    tool_dir.mkdir(parents=True, exist_ok=True)
    wasm_path = tool_dir / f"{name}.wasm"
    wasm_path.write_bytes(wasm_bytes)
    if signature_b64 is not None:
        (tool_dir / f"{name}.wasm.sig").write_text(signature_b64, encoding="utf-8")

    spec = {
        "name": name,
        "version": "0.1.0",
        "description": f"test tool {name}",
        "owner": "claude-code-tests",
        "wasm": f"{name}.wasm",
        "schema": "schema.json",
        "allowed_agents": allowed_agents or [],
        "capability_class": "small",
    }
    (tool_dir / "tool.yaml").write_text(yaml.safe_dump(spec), encoding="utf-8")

    schema = {
        "input": input_schema or {
            "type": "object",
            "required": ["text"],
            "properties": {"text": {"type": "string"}},
            "additionalProperties": False,
        },
        "output": output_schema or {
            "type": "object",
            "required": ["echoed"],
            "properties": {"echoed": {"type": "string"}},
            "additionalProperties": True,
        },
    }
    (tool_dir / "schema.json").write_text(json.dumps(schema), encoding="utf-8")
    return tool_dir


# --- tests --------------------------------------------------------------

def test_registry_discovers_tools(tmp_path):
    _make_tool(tmp_path, "alpha")
    _make_tool(tmp_path, "beta")
    registry = ToolRegistry(
        tools_root=tmp_path,
        verifier=AllowAllVerifier(),
        executor=FakeExecutor({"echoed": "x"}),
    )
    assert registry.names() == ["alpha", "beta"]


def test_registry_skips_directories_without_tool_yaml(tmp_path):
    _make_tool(tmp_path, "alpha")
    (tmp_path / "junk").mkdir()
    (tmp_path / "junk" / "README.md").write_text("not a tool")
    registry = ToolRegistry(
        tools_root=tmp_path,
        verifier=AllowAllVerifier(),
        executor=FakeExecutor({"echoed": "x"}),
    )
    assert registry.names() == ["alpha"]


def test_registry_skips_invalid_tool_yaml(tmp_path, caplog):
    _make_tool(tmp_path, "alpha")
    bad = tmp_path / "broken"
    bad.mkdir()
    (bad / "tool.yaml").write_text("name: broken\n")  # missing version/wasm
    registry = ToolRegistry(
        tools_root=tmp_path,
        verifier=AllowAllVerifier(),
        executor=FakeExecutor({"echoed": "x"}),
    )
    assert "alpha" in registry.names()
    assert "broken" not in registry.names()


def test_get_raises_on_unknown_tool(tmp_path):
    registry = ToolRegistry(
        tools_root=tmp_path,
        verifier=AllowAllVerifier(),
        executor=FakeExecutor({"echoed": "x"}),
    )
    with pytest.raises(UnknownToolError):
        registry.get("nope")


async def test_execute_enforces_agent_acl(tmp_path):
    _make_tool(tmp_path, "restricted", allowed_agents=["analyst"])
    registry = ToolRegistry(
        tools_root=tmp_path,
        verifier=AllowAllVerifier(),
        executor=FakeExecutor({"echoed": "ok"}),
    )
    # analyst is on the list -> ok
    output = await registry.execute("analyst", "restricted", {"text": "hi"})
    assert output == {"echoed": "ok"}

    # echo is not on the list -> reject
    with pytest.raises(ToolNotAllowedError):
        await registry.execute("echo", "restricted", {"text": "hi"})


async def test_execute_rejects_bad_input_schema(tmp_path):
    _make_tool(tmp_path, "strict_in")
    registry = ToolRegistry(
        tools_root=tmp_path,
        verifier=AllowAllVerifier(),
        executor=FakeExecutor({"echoed": "ok"}),
    )
    with pytest.raises(SchemaValidationError, match="input schema"):
        await registry.execute("analyst", "strict_in", {"not_text": 1})


async def test_execute_rejects_bad_output_schema(tmp_path):
    _make_tool(tmp_path, "wonky_out")
    # FakeExecutor returns {"echoed": ...} but we declare the tool returns {"value": int}
    # by overriding the output_schema in the fixture.
    schema_path = tmp_path / "wonky_out" / "schema.json"
    schema_path.write_text(json.dumps({
        "input": {"type": "object", "required": ["text"]},
        "output": {"type": "object", "required": ["value"], "properties": {"value": {"type": "integer"}}},
    }))

    registry = ToolRegistry(
        tools_root=tmp_path,
        verifier=AllowAllVerifier(),
        executor=FakeExecutor({"echoed": "ok"}),  # missing "value"
    )
    with pytest.raises(SchemaValidationError, match="output schema|does not match"):
        await registry.execute("analyst", "wonky_out", {"text": "x"})


async def test_execute_verifies_signature_when_present(tmp_path):
    priv, pub = generate_test_keypair()
    wasm_bytes = b"\0asm\x01\x00\x00\x00" + b"\x00" * 16
    valid_sig = sign_blob_for_testing(wasm_bytes, priv)

    _make_tool(tmp_path, "signed", wasm_bytes=wasm_bytes, signature_b64=valid_sig)
    registry = ToolRegistry(
        tools_root=tmp_path,
        verifier=CosignVerifier(pub),
        executor=FakeExecutor({"echoed": "ok"}),
    )
    output = await registry.execute("analyst", "signed", {"text": "hi"})
    assert output == {"echoed": "ok"}


async def test_execute_rejects_invalid_signature(tmp_path):
    priv, pub = generate_test_keypair()
    wasm_bytes = b"\0asm\x01\x00\x00\x00original"
    # Sign different bytes, then deploy "tampered" bytes.
    valid_sig_for_other = sign_blob_for_testing(b"different bytes", priv)

    _make_tool(tmp_path, "tampered", wasm_bytes=wasm_bytes, signature_b64=valid_sig_for_other)
    registry = ToolRegistry(
        tools_root=tmp_path,
        verifier=CosignVerifier(pub),
        executor=FakeExecutor({"echoed": "should not run"}),
    )
    with pytest.raises(SignatureVerificationError):
        await registry.execute("analyst", "tampered", {"text": "hi"})
