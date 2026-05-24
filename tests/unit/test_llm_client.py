"""Unit tests for `libs/llm/client.py`.

Focus areas:

  * `chat_json` backward compatibility — Sprint 2 callers that don't
    pass `response_schema` still get a plain dict.
  * `chat_json` schema validation path — supplied schema validates and
    returns a model instance.
  * `LLMOutputValidationError` shape — wraps the raw output and the
    underlying Pydantic error, subclasses `ValueError` so existing
    handlers catch it.

We exercise these via `StubLLMClient`. The real `AnthropicClient`
path uses the same `_maybe_validate` helper, so coverage of one
covers the other for validation semantics.
"""
from __future__ import annotations

import pytest
from pydantic import BaseModel, Field, ValidationError

from libs.llm import LLMOutputValidationError, StubLLMClient

pytestmark = [pytest.mark.unit]


class DateRange(BaseModel):
    start: str
    end: str


class IntentReply(BaseModel):
    """Mirrors what Sprint 2's intent_parser_node prompt asks for."""

    objective: str
    domain: str
    requires_clarification: bool = False
    constraints: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------- #
# Backward compatibility — no schema = same shape as before
# ---------------------------------------------------------------- #

async def test_chat_json_without_schema_returns_dict_unchanged():
    """Sprint 2 nodes don't pass response_schema; behavior must not change."""
    stub = StubLLMClient(responses=[{"objective": "draft a settlement", "domain": "employment_law"}])
    result = await stub.chat_json("any prompt")
    assert isinstance(result, dict)
    assert result == {"objective": "draft a settlement", "domain": "employment_law"}


async def test_chat_json_without_schema_does_not_raise_on_extra_fields():
    """No schema = no validation = any dict shape is acceptable."""
    stub = StubLLMClient(responses=[{"weird": "shape", "no_required_fields": True}])
    result = await stub.chat_json("any prompt")
    assert result["weird"] == "shape"


# ---------------------------------------------------------------- #
# Schema path — validation succeeds
# ---------------------------------------------------------------- #

async def test_chat_json_with_schema_returns_validated_model_instance():
    stub = StubLLMClient(responses=[{
        "objective": "draft a settlement",
        "domain": "employment_law",
        "requires_clarification": False,
        "constraints": ["UK jurisdiction"],
    }])
    result = await stub.chat_json("any", response_schema=IntentReply)

    assert isinstance(result, IntentReply)
    assert result.objective == "draft a settlement"
    assert result.constraints == ["UK jurisdiction"]


async def test_chat_json_with_schema_fills_default_fields():
    """Schema defaults apply when the LLM omits optional fields."""
    stub = StubLLMClient(responses=[{
        "objective": "x",
        "domain": "general",
        # requires_clarification + constraints omitted
    }])
    result = await stub.chat_json("any", response_schema=IntentReply)
    assert result.requires_clarification is False
    assert result.constraints == []


async def test_chat_json_with_nested_schema():
    class Reply(BaseModel):
        ranges: list[DateRange]

    stub = StubLLMClient(responses=[{"ranges": [
        {"start": "2026-01-01", "end": "2026-03-31"},
        {"start": "2026-04-01", "end": "2026-06-30"},
    ]}])
    result = await stub.chat_json("any", response_schema=Reply)
    assert len(result.ranges) == 2
    assert isinstance(result.ranges[0], DateRange)
    assert result.ranges[0].start == "2026-01-01"


# ---------------------------------------------------------------- #
# Schema path — validation fails
# ---------------------------------------------------------------- #

async def test_chat_json_with_schema_raises_when_required_field_missing():
    stub = StubLLMClient(responses=[{"domain": "employment_law"}])   # missing `objective`
    with pytest.raises(LLMOutputValidationError) as excinfo:
        await stub.chat_json("any", response_schema=IntentReply)
    assert "IntentReply" in str(excinfo.value)


async def test_chat_json_with_schema_raises_when_field_wrong_type():
    stub = StubLLMClient(responses=[{
        "objective": "x",
        "domain": "general",
        "requires_clarification": "not-a-bool",
    }])
    with pytest.raises(LLMOutputValidationError):
        await stub.chat_json("any", response_schema=IntentReply)


async def test_validation_error_exposes_raw_output_and_pydantic_error():
    """Callers can introspect what went wrong."""
    bad_payload = {"domain": "employment_law"}   # missing objective
    stub = StubLLMClient(responses=[bad_payload])
    with pytest.raises(LLMOutputValidationError) as excinfo:
        await stub.chat_json("any", response_schema=IntentReply)
    err = excinfo.value
    # raw_output is the dict we got from the LLM
    assert err.raw_output == bad_payload
    # pydantic_error is the original ValidationError, useful for
    # walking err.pydantic_error.errors() programmatically.
    assert isinstance(err.pydantic_error, ValidationError)
    assert any(e["type"] == "missing" for e in err.pydantic_error.errors())


async def test_validation_error_is_a_value_error_for_backward_compat():
    """Sprint 2 nodes catch ValueError from _parse_json — they should
    also catch validation failures via the same handler if they opt in."""
    stub = StubLLMClient(responses=[{"objective": "x"}])   # missing domain
    with pytest.raises(ValueError):
        await stub.chat_json("any", response_schema=IntentReply)


# ---------------------------------------------------------------- #
# Stub's other plumbing still works after the schema kwarg
# ---------------------------------------------------------------- #

async def test_stub_records_prompt_for_assertion_even_with_schema():
    stub = StubLLMClient(responses=[{"objective": "x", "domain": "general"}])
    await stub.chat_json("the prompt", response_schema=IntentReply)
    assert stub.calls == ["the prompt"]


async def test_stub_exhausted_raises_runtime_error_with_or_without_schema():
    """Same exhaustion behavior regardless of schema usage."""
    stub = StubLLMClient(responses=[])
    with pytest.raises(RuntimeError, match="exhausted"):
        await stub.chat_json("any")
    with pytest.raises(RuntimeError, match="exhausted"):
        await stub.chat_json("any", response_schema=IntentReply)
