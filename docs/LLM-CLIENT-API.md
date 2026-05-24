# LLM Client API — `libs/llm/client.py`

Reference for the abstraction Sprint 2 + Sprint 6 + Sprint 11 agents use to call
language models. The two methods that matter are `chat_json` and `chat_with_tools`;
this doc focuses on `chat_json` schema validation (added in Sprint 11 follow-up).

`chat_with_tools` is documented inline in `libs/llm/tools.py` and covered by
the Sprint 6 agent_loop tests; cross-reference there if you're integrating
tool use.

---

## TL;DR

```python
from pydantic import BaseModel
from libs.llm import build_default_client, LLMOutputValidationError

class Intent(BaseModel):
    objective: str
    domain: str

llm = build_default_client()

# Without schema → returns dict (backward compatible)
raw: dict = await llm.chat_json("Extract intent: ...")

# With schema → returns validated model instance
intent: Intent = await llm.chat_json("Extract intent: ...", response_schema=Intent)

# Validation failure → catchable exception
try:
    intent = await llm.chat_json("...", response_schema=Intent)
except LLMOutputValidationError as e:
    print(e.raw_output)       # the dict the LLM returned
    print(e.pydantic_error)   # the wrapped pydantic.ValidationError
```

---

## `LLMClient.chat_json`

```python
async def chat_json(
    self,
    prompt: str,
    *,
    response_schema: type[BaseModel] | None = None,
) -> dict[str, Any] | BaseModel: ...
```

Send a prompt that the model is expected to answer with a single JSON object.
The implementation strips common markdown code fences (e.g. ` ```json `) before
parsing, so prompts that say "respond with JSON" without explicitly forbidding
fences still work.

### Parameters

| Name | Type | Required | Notes |
|---|---|---|---|
| `prompt` | `str` | yes | Positional. Plain string; caller is responsible for telling the model which fields the JSON must contain. |
| `response_schema` | `type[BaseModel]` or `None` | no, keyword-only | When provided, the parsed JSON is validated against this Pydantic model and the method returns a model instance. When omitted, the raw `dict` is returned (the Sprint 2 behavior). |

`response_schema` is **keyword-only** (the `*` in the signature). This is deliberate:
prevents accidental positional swapping with `prompt`.

### Return type

Two overloads are declared so static type checkers (pyright, mypy) infer the
right type per call site:

```python
@overload
async def chat_json(self, prompt: str) -> dict[str, Any]: ...
@overload
async def chat_json(self, prompt: str, *, response_schema: type[T]) -> T: ...
```

- **No schema:** `dict[str, Any]` — exactly what `json.loads` produced.
- **With schema:** an instance of the schema class, with all defaults applied
  and field types coerced per Pydantic's rules.

### Exceptions

| Exception | When |
|---|---|
| `ValueError` | The LLM's response is not parseable JSON, even after stripping fences. Message includes the first 200 chars of the raw text. |
| `LLMOutputValidationError` | JSON parses but doesn't match `response_schema`. Subclasses `ValueError` so existing `except ValueError` handlers catch it. |
| `RuntimeError` | (Stub only) the stub's response queue is exhausted. Production callers won't see this. |

`LLMOutputValidationError` carries two attributes you can inspect:

```python
except LLMOutputValidationError as e:
    e.raw_output      # dict[str, Any]   — what the LLM actually returned
    e.pydantic_error  # pydantic.ValidationError — for .errors() introspection
```

---

## `LLMOutputValidationError`

```python
class LLMOutputValidationError(ValueError):
    raw_output: dict[str, Any]
    pydantic_error: pydantic.ValidationError
```

Subclasses `ValueError` for backward compatibility — Sprint 2 nodes that
already wrap LLM calls in `try / except ValueError` continue to work without
changes when callers start passing schemas.

The wrapped `pydantic_error.errors()` returns a list of per-field error dicts
useful for surfacing structured failure info to retry logic or to the UI.

---

## Implementations

### `AnthropicClient`

Real client. Wraps `langchain_anthropic.ChatAnthropic` for `chat_json` and the
raw `anthropic.AsyncAnthropic` SDK for `chat_with_tools` (bypassing langchain's
tool abstraction to keep raw `tool_use` blocks intact).

- Reads `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` from the environment.
- Default model: `claude-sonnet-4-6`.
- Default temperature: `0.0` (deterministic for evals).

### `StubLLMClient`

In-process test double. Takes a list of canned responses; each call to
`chat_json` pops the next one. Schema validation runs on the stub responses
too, so you can exercise validation-failure paths without an API key:

```python
from libs.llm import StubLLMClient

stub = StubLLMClient(responses=[
    {"objective": "draft NDA", "domain": "contract_law"},     # passes Intent
    {"domain": "contract_law"},                                # fails — missing objective
])

intent = await stub.chat_json("any", response_schema=Intent)   # ok
with pytest.raises(LLMOutputValidationError):
    await stub.chat_json("any", response_schema=Intent)
```

The stub also tracks invocations:

- `stub.calls: list[str]` — prompts seen, in order
- `stub.tool_calls: list[dict]` — `chat_with_tools` invocations (deep-copied
  to avoid the agent-loop in-place mutation gotcha)

---

## Building the client

```python
from libs.llm import build_default_client

llm = build_default_client()    # AnthropicClient if ANTHROPIC_API_KEY is set
```

`build_default_client()` raises `RuntimeError` if the env var is missing.
Tests should construct `StubLLMClient` explicitly rather than relying on the
default. This is intentional: a missing API key should never silently fall
back to a stub in production.

---

## Common patterns

### Retry on validation failure

LLMs sometimes return *almost* valid JSON — wrong type on one field, missing
optional that becomes required after a schema change, etc. Pattern:

```python
async def chat_with_retry(llm, prompt, schema, *, max_attempts=3):
    last_err = None
    for attempt in range(max_attempts):
        try:
            return await llm.chat_json(prompt, response_schema=schema)
        except LLMOutputValidationError as exc:
            last_err = exc
            # Append the error to the prompt so the model can self-correct.
            errors_summary = "; ".join(
                f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}"
                for e in exc.pydantic_error.errors()
            )
            prompt = (
                f"{prompt}\n\n"
                f"Previous attempt failed validation: {errors_summary}.\n"
                f"Return JSON matching the schema exactly."
            )
    raise last_err
```

This pushes the validation error back into the model's context. Claude
typically self-corrects on the second attempt. Cap `max_attempts` low —
infinite retries waste tokens.

### Schema versioning

When a schema evolves, bump it explicitly rather than mutating in place:

```python
class IntentV1(BaseModel):
    objective: str
    domain: str

class IntentV2(BaseModel):
    objective: str
    domain: str
    confidence: float = 0.0      # new field, defaulted

# Old callers stay on V1; new callers opt into V2 by passing the new class.
await llm.chat_json(prompt, response_schema=IntentV1)
await llm.chat_json(prompt, response_schema=IntentV2)
```

Don't change `IntentV1`'s fields after callers exist — that breaks them
silently. Treat schemas like API versions.

### Distinguishing "model gave wrong shape" from "no JSON at all"

```python
try:
    result = await llm.chat_json(prompt, response_schema=Reply)
except LLMOutputValidationError as exc:
    # Got JSON, but wrong shape. Retry-with-feedback is reasonable.
    log.warning("schema mismatch: %s", exc.pydantic_error.errors())
    ...
except ValueError as exc:
    # Couldn't even parse as JSON. Model probably wandered off into prose.
    # Retry with stronger formatting instructions or fall back.
    log.warning("non-JSON response: %s", exc)
    ...
```

Two distinct failure modes; two distinct recoveries. The exception hierarchy
makes the distinction at the type level.

### Stricter schemas via Pydantic config

If you want unknown fields to fail validation (catches LLM hallucinations of
extra fields), use Pydantic's strict mode:

```python
class StrictIntent(BaseModel):
    model_config = {"extra": "forbid"}    # reject any field not declared

    objective: str
    domain: str
```

Useful for security-sensitive callers (e.g. the Compliance Officer's verdict)
where you don't want the LLM smuggling in fields you haven't designed for.

---

## What this isn't

- **Not a JSON schema generator.** Pydantic v2 has `Model.model_json_schema()`
  if you want to embed the schema in the prompt. That's a caller decision —
  some prompts work better with the schema inline, others with field-name
  hints only.
- **Not a streaming interface.** `chat_json` waits for the full response,
  then validates. Streaming + schema validation is incompatible because
  validation requires the complete object.
- **Not a tool-use entry point.** Tool calls go through `chat_with_tools` /
  `agent_loop` (see `libs/llm/tools.py`). `chat_json` is for "one prompt,
  one structured reply."

---

## Tests

`tests/unit/test_llm_client.py` — 11 unit tests:

- Backward compat (no schema → dict, no validation, no breakage)
- Happy path with schema (returns model, defaults applied, nested types work)
- Failure modes (missing required field, wrong type)
- Error introspection (`raw_output`, `pydantic_error.errors()`)
- Subclass invariant (`LLMOutputValidationError` IS a `ValueError`)
- Stub plumbing (call recording, exhaustion behavior)

Run them:

```bash
pytest tests/unit/test_llm_client.py -v
```

---

## Changelog

| Sprint | Change |
|---|---|
| 2 | Initial `LLMClient` Protocol + `AnthropicClient` + `StubLLMClient`. `chat_json(prompt) -> dict`. |
| 6 | Added `chat_with_tools` for Claude tool-use protocol; `agent_loop()` helper. |
| 11 (follow-up) | `chat_json` gained optional `response_schema` kwarg + `LLMOutputValidationError`. Backward compatible. |
