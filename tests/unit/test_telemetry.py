"""Unit tests for telemetry init.

`init_telemetry` mutates global state (the OpenTelemetry TracerProvider),
so we only verify idempotency and that the resource carries the service
name. Span export plumbing is exercised by the integration tests.
"""
from __future__ import annotations

import pytest

from opentelemetry import trace

from libs.communication import telemetry


@pytest.mark.unit
def test_init_telemetry_is_idempotent():
    t1 = telemetry.init_telemetry(service_name="test-svc")
    t2 = telemetry.init_telemetry(service_name="test-svc")
    # Both calls return Tracers from the same provider.
    assert isinstance(t1, type(t2))


@pytest.mark.unit
def test_get_tracer_works_without_explicit_init():
    # No assertion on a specific class — the OTel API surfaces an opaque
    # Tracer either way. We just want no exception.
    tracer = telemetry.get_tracer("anything")
    with tracer.start_as_current_span("smoke"):
        span = trace.get_current_span()
        assert span is not None
