"""Prompt templates for the Orchestrator's LLM nodes.

Kept in a dedicated module so prompt edits don't touch graph logic and so
the templates can be unit-tested for required placeholders.
"""

from __future__ import annotations

INTENT_PROMPT = """\
You are an intent parser. Extract the user's request into a structured format.

USER REQUEST:
{user_request}

Respond ONLY with a valid JSON object (no markdown, no commentary):
{{
    "objective": "single-sentence summary of what the user wants",
    "domain": "employment_law|contract_law|cybersecurity|finance|general",
    "scope": "short description of bounds (e.g. UK jurisdiction, single contract)",
    "constraints": ["list of explicit constraints from the request"],
    "ambiguities": ["list of underspecified aspects that may need clarification"],
    "requires_clarification": true_or_false,
    "clarification_questions": ["questions to ask the user if requires_clarification is true"]
}}
"""

DECOMPOSE_PROMPT = """\
You are a task decomposer. Break the objective into atomic, executable subtasks.

OBJECTIVE: {objective}
DOMAIN: {domain}
CONSTRAINTS: {constraints}

Each task must be assignable to exactly ONE of these agents:
- "domain_analyst": research, analysis, evidence gathering
- "compliance_officer": regulatory verification, risk flagging
- "editor": formatting, document finalization

Respond ONLY with a valid JSON object (no markdown):
{{
    "tasks": [
        {{
            "id": "task_1",
            "name": "short task name",
            "description": "what the agent should do",
            "assigned_to": "domain_analyst|compliance_officer|editor",
            "inputs": {{}},
            "expected_outputs": ["names of expected output fields"],
            "depends_on": [],
            "priority": "critical|high|normal",
            "deadline": null
        }}
    ]
}}
"""
