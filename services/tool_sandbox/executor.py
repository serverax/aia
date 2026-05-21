"""WASM tool executor — the core of Sprint 6's tool sandbox.

Wraps wasmtime-py 24.x with:

  * Fuel-based CPU metering (deterministic; per-invocation budget).
  * Memory cap enforced via Store ResourceLimiter (defense in depth on top
    of the module-level `(memory ... max=N)` declaration).
  * WASI denial-by-default: NO preopened directories, NO inherited env,
    NO inherited network, NO inherited stdin/stdout.
  * stdin/stdout for JSON payloads via temp files (the only I/O path the
    tool has).
  * Sync execution wrapped in `asyncio.to_thread` so agents stay async.

The executor never trusts the tool. It enforces limits at the host level
regardless of what the WASM module declares.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from wasmtime import (
    Config,
    Engine,
    ExitTrap,
    Linker,
    Module,
    Store,
    Trap,
    WasiConfig,
)

logger = logging.getLogger(__name__)


# Defaults sized for "small pure function" tools (parse_dates, validate_*).
# Override per-tool via tool.yaml -> capability_class.
DEFAULT_FUEL = 100_000_000          # ~100 ms on a typical CPU
DEFAULT_MEMORY_BYTES = 64 * 1024 * 1024   # 64 MiB
DEFAULT_WALL_TIMEOUT_SECONDS = 5.0   # Hard upper bound even if fuel undercounts


@dataclass(frozen=True)
class ExecutionLimits:
    """Per-invocation resource budget.

    Fuel maps roughly to CPU cycles consumed. Memory is enforced on every
    grow() the module attempts. Wall timeout is the hard guard — if the
    module is stuck in a host call (rare with our WASI denial), this
    kicks in.
    """

    fuel: int = DEFAULT_FUEL
    memory_bytes: int = DEFAULT_MEMORY_BYTES
    wall_timeout_seconds: float = DEFAULT_WALL_TIMEOUT_SECONDS


@dataclass
class ExecutionResult:
    """Output of a single tool invocation."""

    output: dict[str, Any] = field(default_factory=dict)
    fuel_consumed: int | None = None
    wall_seconds: float = 0.0
    stderr: str = ""

    @property
    def succeeded(self) -> bool:
        return "error" not in self.output


class ExecutionError(RuntimeError):
    """Raised when a tool invocation fails at the host level (trap, OOM,
    timeout, malformed output JSON, etc.). Tool-level errors (the tool
    returning `{"error": "..."}`) surface in `ExecutionResult.output`."""


class WasmExecutor:
    """Loads .wasm bytes once per call (no shared cache — simpler audit story)."""

    def __init__(self, default_limits: ExecutionLimits | None = None) -> None:
        self.default_limits = default_limits or ExecutionLimits()

    async def execute(
        self,
        wasm_bytes: bytes,
        input_payload: dict[str, Any],
        *,
        limits: ExecutionLimits | None = None,
        tool_name: str = "<anonymous>",
    ) -> ExecutionResult:
        """Run a WASI command module with the given JSON input.

        Off-loads the sync wasmtime call into a thread so the calling
        agent's event loop stays responsive.
        """
        effective = limits or self.default_limits
        input_json = json.dumps(input_payload, ensure_ascii=False, sort_keys=True)
        return await asyncio.wait_for(
            asyncio.to_thread(self._execute_sync, wasm_bytes, input_json, effective, tool_name),
            timeout=effective.wall_timeout_seconds,
        )

    # --- internals -------------------------------------------------------

    def _execute_sync(
        self,
        wasm_bytes: bytes,
        input_json: str,
        limits: ExecutionLimits,
        tool_name: str,
    ) -> ExecutionResult:
        config = Config()
        config.consume_fuel = True
        engine = Engine(config)

        store = Store(engine)
        store.set_fuel(limits.fuel)
        store.set_limits(memory_size=limits.memory_bytes)

        linker = Linker(engine)
        linker.define_wasi()

        # Write input to temp file (stdin), capture stdout/stderr to temp files.
        # NamedTemporaryFile(delete=False) is needed on Windows since wasmtime
        # opens the file by path while Python still holds the handle.
        with tempfile.TemporaryDirectory(prefix=f"wasm-{tool_name}-") as workdir:
            stdin_path = Path(workdir) / "in.json"
            stdout_path = Path(workdir) / "out.json"
            stderr_path = Path(workdir) / "err.log"
            stdin_path.write_text(input_json, encoding="utf-8")

            wasi = WasiConfig()
            # Maximum lockdown: no env, no network, no preopen, no inherited fds.
            wasi.stdin_file = str(stdin_path)
            wasi.stdout_file = str(stdout_path)
            wasi.stderr_file = str(stderr_path)
            store.set_wasi(wasi)

            module = Module(engine, wasm_bytes)
            instance = linker.instantiate(store, module)

            start = instance.exports(store).get("_start")
            if start is None:
                raise ExecutionError(
                    f"tool {tool_name!r} is not a WASI command module (missing _start)"
                )

            import time

            t0 = time.perf_counter()
            try:
                start(store)
            except ExitTrap as trap:
                # WASI command modules normally terminate by calling
                # proc_exit(0); wasmtime-py surfaces that as ExitTrap.
                # Non-zero exits are tool-level failures we still want to
                # surface output for (the tool may have written an error
                # envelope to stdout).
                exit_status = getattr(trap, "exit_status", None)
                if exit_status not in (0, None):
                    logger.info("tool %s exited %s", tool_name, exit_status)
            except Trap as trap:
                # Genuine WASM trap (fuel exhaustion, memory violation,
                # invalid instruction). The output JSON parse below will
                # likely fail; the host raises ExecutionError there.
                logger.warning("tool %s trapped: %s", tool_name, trap)
            elapsed = time.perf_counter() - t0

            stdout_text = _read_text(stdout_path)
            stderr_text = _read_text(stderr_path)

            if not stdout_text.strip():
                raise ExecutionError(
                    f"tool {tool_name!r} produced no stdout (stderr: {stderr_text!r})"
                )
            try:
                output = json.loads(stdout_text)
            except json.JSONDecodeError as exc:
                raise ExecutionError(
                    f"tool {tool_name!r} stdout is not valid JSON: {exc}; raw={stdout_text!r}"
                ) from exc
            if not isinstance(output, dict):
                raise ExecutionError(
                    f"tool {tool_name!r} stdout JSON must be an object, got {type(output).__name__}"
                )

            fuel_left = _safe_fuel(store)
            consumed = (limits.fuel - fuel_left) if fuel_left is not None else None

            return ExecutionResult(
                output=output,
                fuel_consumed=consumed,
                wall_seconds=elapsed,
                stderr=stderr_text,
            )


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def _safe_fuel(store: Store) -> int | None:
    """Best-effort fuel readout; wasmtime-py version drift makes this risky."""
    try:
        return store.get_fuel()
    except Exception:  # pragma: no cover - older wasmtime-py
        return None
