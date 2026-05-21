"""OpenTelemetry initialization with OTLP/gRPC export to Jaeger.

Jaeger 1.35+ accepts OTLP directly on :4317, so we use the OTLP exporter
rather than the deprecated Jaeger Thrift exporter. Call `init_telemetry`
once at service startup; afterwards use `tracer = trace.get_tracer(...)`
from the OpenTelemetry API anywhere in the codebase.
"""
from __future__ import annotations

import logging
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Tracer

logger = logging.getLogger(__name__)

_initialized = False


def init_telemetry(
    service_name: str | None = None,
    service_version: str = "0.1.0",
    otlp_endpoint: str | None = None,
    console_fallback: bool = True,
) -> Tracer:
    """Initialize the global TracerProvider. Idempotent.

    Args:
        service_name: Identifier reported as `service.name`. Falls back to
            $OTEL_SERVICE_NAME, then "unknown_service".
        service_version: Reported as `service.version`.
        otlp_endpoint: gRPC endpoint for Jaeger/OTLP collector. Falls back
            to $OTEL_EXPORTER_OTLP_ENDPOINT, then no OTLP exporter is added.
        console_fallback: If True and no OTLP endpoint is configured, add a
            console exporter so spans are still visible during local dev.

    Returns:
        A Tracer scoped to this service.
    """
    global _initialized

    name = service_name or os.environ.get("OTEL_SERVICE_NAME") or "unknown_service"
    endpoint = otlp_endpoint or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")

    if _initialized:
        return trace.get_tracer(name)

    resource = Resource.create(
        {SERVICE_NAME: name, SERVICE_VERSION: service_version}
    )
    provider = TracerProvider(resource=resource)

    if endpoint:
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
        )
        logger.info("OTLP exporter configured: %s", endpoint)
    elif console_fallback:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        logger.info("No OTLP endpoint set; using ConsoleSpanExporter")

    trace.set_tracer_provider(provider)
    _initialized = True

    return trace.get_tracer(name)


def get_tracer(name: str | None = None) -> Tracer:
    """Convenience accessor. Safe to call before `init_telemetry`."""
    return trace.get_tracer(name or "default")
