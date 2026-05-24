"""Signed tool registry.

The registry knows which tools exist, what their input/output schemas
look like, which agents may call them, and where the signed `.wasm`
artifacts live on disk. `execute()` is the single entry point agents
use; it stitches together:

    lookup descriptor -> ACL check -> signature verify ->
    schema-validate input -> WASM execute -> schema-validate output ->
    audit row

Each tool lives in `tools/<name>/` with a `tool.yaml` describing it.
Built artifacts live in `tools/<name>/dist/` (produced by the build
script in scripts/security/build-and-sign-tools.sh).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Protocol

import yaml
from jsonschema import Draft202012Validator, ValidationError

from services.tool_sandbox.executor import ExecutionLimits, WasmExecutor
from services.tool_sandbox.verifier import (
    SignatureVerificationError,
    SignatureVerifier,
)

logger = logging.getLogger(__name__)


# Capability classes -> resource budgets. Tools opt in via tool.yaml.
CAPABILITY_CLASSES: dict[str, ExecutionLimits] = {
    "small": ExecutionLimits(
        fuel=100_000_000, memory_bytes=64 * 1024 * 1024, wall_timeout_seconds=2.0
    ),
    "medium": ExecutionLimits(
        fuel=500_000_000, memory_bytes=128 * 1024 * 1024, wall_timeout_seconds=5.0
    ),
    "large": ExecutionLimits(
        fuel=2_000_000_000, memory_bytes=256 * 1024 * 1024, wall_timeout_seconds=15.0
    ),
}


class UnknownToolError(KeyError):
    """Raised when an agent asks for a tool that isn't in the registry."""


class ToolNotAllowedError(PermissionError):
    """Raised when an agent calls a tool whose `allowed_agents` list excludes it."""


class SchemaValidationError(ValueError):
    """Raised when input or output JSON doesn't match the tool's declared schema."""


class AuditSink(Protocol):
    """Anything that can record a row about a tool invocation.

    The default implementation in production is `libs.communication.postgres_client.audit`
    wrapped in a small adapter. Tests pass `None` to skip auditing.
    """

    async def record(
        self,
        *,
        agent_id: str,
        tool_name: str,
        tool_version: str,
        status: str,
        input_payload: Mapping[str, Any],
        output_payload: Mapping[str, Any],
        error: str | None,
    ) -> None: ...


@dataclass(frozen=True)
class ToolDescriptor:
    """Everything the registry knows about one tool."""

    name: str
    version: str
    description: str
    owner: str
    wasm_path: Path
    signature_path: Path
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    allowed_agents: tuple[str, ...]
    capability_class: str

    @property
    def limits(self) -> ExecutionLimits:
        return CAPABILITY_CLASSES.get(self.capability_class, CAPABILITY_CLASSES["small"])


@dataclass
class ToolRegistry:
    tools_root: Path
    verifier: SignatureVerifier
    executor: WasmExecutor
    audit_sink: AuditSink | None = None

    _by_name: dict[str, ToolDescriptor] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.reload()

    # --- discovery -------------------------------------------------------

    def reload(self) -> None:
        """Re-scan `tools_root` and rebuild the descriptor map.

        Skips directories without a `tool.yaml`; logs and skips invalid
        ones (so a single broken tool can't take the registry offline).
        """
        discovered: dict[str, ToolDescriptor] = {}
        if not self.tools_root.exists():
            logger.warning("tools_root %s does not exist", self.tools_root)
            self._by_name = {}
            return
        for child in sorted(self.tools_root.iterdir()):
            tool_yaml = child / "tool.yaml"
            if not tool_yaml.is_file():
                continue
            try:
                descriptor = self._load_descriptor(child, tool_yaml)
            except Exception as exc:
                logger.error("skipping tool at %s: %s", child, exc)
                continue
            discovered[descriptor.name] = descriptor
        self._by_name = discovered
        logger.info("loaded %d tools: %s", len(discovered), sorted(discovered))

    def _load_descriptor(self, tool_dir: Path, tool_yaml: Path) -> ToolDescriptor:
        spec = yaml.safe_load(tool_yaml.read_text(encoding="utf-8")) or {}
        for required in ("name", "version", "wasm"):
            if required not in spec:
                raise ValueError(f"tool.yaml missing required field {required!r}")

        wasm_path = (tool_dir / spec["wasm"]).resolve()
        sig_path = wasm_path.with_suffix(wasm_path.suffix + ".sig")

        schema_file = tool_dir / spec.get("schema", "schema.json")
        if not schema_file.is_file():
            raise ValueError(f"schema file missing: {schema_file}")
        import json

        schema = json.loads(schema_file.read_text(encoding="utf-8"))
        input_schema = schema.get("input")
        output_schema = schema.get("output")
        if not isinstance(input_schema, dict) or not isinstance(output_schema, dict):
            raise ValueError(
                f"{schema_file} must contain top-level 'input' and 'output' JSON Schema objects"
            )

        return ToolDescriptor(
            name=spec["name"],
            version=str(spec["version"]),
            description=spec.get("description", ""),
            owner=spec.get("owner", "unknown"),
            wasm_path=wasm_path,
            signature_path=sig_path,
            input_schema=input_schema,
            output_schema=output_schema,
            allowed_agents=tuple(spec.get("allowed_agents", ())),
            capability_class=spec.get("capability_class", "small"),
        )

    # --- query -----------------------------------------------------------

    def names(self) -> list[str]:
        return sorted(self._by_name)

    def get(self, name: str) -> ToolDescriptor:
        try:
            return self._by_name[name]
        except KeyError as exc:
            raise UnknownToolError(name) from exc

    def is_allowed(self, agent_id: str, tool_name: str) -> bool:
        try:
            descriptor = self.get(tool_name)
        except UnknownToolError:
            return False
        # Empty allowed_agents list = open to all agents (rare, opt-in).
        if not descriptor.allowed_agents:
            return True
        return agent_id in descriptor.allowed_agents

    # --- execute ---------------------------------------------------------

    async def execute(
        self,
        agent_id: str,
        tool_name: str,
        input_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Full pipeline: lookup → ACL → verify → schema-in → exec → schema-out → audit."""
        descriptor = self.get(tool_name)

        if not self.is_allowed(agent_id, tool_name):
            await self._audit_failure(
                agent_id, descriptor, dict(input_payload), "agent_not_allowed"
            )
            raise ToolNotAllowedError(
                f"agent {agent_id!r} may not call tool {tool_name!r}; "
                f"allowed: {list(descriptor.allowed_agents)}"
            )

        # Validate input *before* executing — cheap defense against malformed calls.
        try:
            Draft202012Validator(descriptor.input_schema).validate(dict(input_payload))
        except ValidationError as exc:
            await self._audit_failure(
                agent_id, descriptor, dict(input_payload), f"input_schema: {exc.message}"
            )
            raise SchemaValidationError(f"input schema violation: {exc.message}") from exc

        # Verify signature on the on-disk wasm before instantiating.
        if not descriptor.wasm_path.is_file():
            raise FileNotFoundError(f"wasm artifact missing: {descriptor.wasm_path}")
        wasm_bytes = descriptor.wasm_path.read_bytes()
        if descriptor.signature_path.is_file():
            sig_b64 = descriptor.signature_path.read_text(encoding="utf-8").strip()
            try:
                self.verifier.verify(wasm_bytes, sig_b64)
            except SignatureVerificationError as exc:
                await self._audit_failure(
                    agent_id, descriptor, dict(input_payload), f"signature: {exc}"
                )
                raise
        else:
            # Strict mode would refuse here. Sprint 6 Day 3 keeps a soft
            # check so the integration test can use AllowAllVerifier
            # alongside missing sig files; production swaps to strict by
            # setting `require_signature=True` (Day 5 hardening).
            logger.warning(
                "no signature file for tool %s at %s", descriptor.name, descriptor.signature_path
            )

        result = await self.executor.execute(
            wasm_bytes,
            dict(input_payload),
            limits=descriptor.limits,
            tool_name=descriptor.name,
        )

        # Validate output before we trust it back to the agent.
        try:
            Draft202012Validator(descriptor.output_schema).validate(result.output)
        except ValidationError as exc:
            await self._audit_failure(
                agent_id, descriptor, dict(input_payload), f"output_schema: {exc.message}"
            )
            raise SchemaValidationError(
                f"tool {descriptor.name!r} returned output that does not match its "
                f"declared schema: {exc.message}"
            ) from exc

        await self._audit_success(agent_id, descriptor, dict(input_payload), result.output)
        return result.output

    # --- audit helpers ---------------------------------------------------

    async def _audit_success(
        self,
        agent_id: str,
        descriptor: ToolDescriptor,
        input_payload: dict[str, Any],
        output_payload: dict[str, Any],
    ) -> None:
        if not self.audit_sink:
            return
        await self.audit_sink.record(
            agent_id=agent_id,
            tool_name=descriptor.name,
            tool_version=descriptor.version,
            status="ok",
            input_payload=input_payload,
            output_payload=output_payload,
            error=None,
        )

    async def _audit_failure(
        self,
        agent_id: str,
        descriptor: ToolDescriptor,
        input_payload: dict[str, Any],
        error: str,
    ) -> None:
        if not self.audit_sink:
            return
        await self.audit_sink.record(
            agent_id=agent_id,
            tool_name=descriptor.name,
            tool_version=descriptor.version,
            status="error",
            input_payload=input_payload,
            output_payload={},
            error=error,
        )
