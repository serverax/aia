"""Editor / Finalizer agent — Redis-stream transport for document generation.

The document *rendering* logic (DOCX/PDF/Markdown→HTML) already exists at
``cursor/services/editor_agent/generator`` (docx_generator, pdf_generator,
schema_validator). What was missing — and what lives here — is the
event-driven transport that lets the Editor participate in orchestration:
consume task assignments from Redis, render, and publish the artifact back.

On integration, inject the real generator via the ``renderer`` argument of
:class:`~services.editor_agent.main.EditorAgent`; the built-in default is a
minimal self-contained Markdown renderer so this service is runnable and
testable on its own.
"""
