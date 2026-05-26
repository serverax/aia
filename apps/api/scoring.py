"""Candidate scoring.

Two scorers behind one :class:`Scorer` protocol:

* :class:`LLMScorer` — asks Claude (via ``libs.llm``) for a structured score.
* :class:`HeuristicScorer` — deterministic keyword-overlap fallback so the
  endpoint always works, including in CI where no API key is present.

:func:`build_scorer` picks the LLM scorer when an Anthropic key is configured,
otherwise the heuristic. The LLM scorer also degrades to the heuristic if the
model returns something unparseable, tagging the result so callers can tell.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Protocol

from .schemas import ScoreResult

logger = logging.getLogger(__name__)

_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "in",
    "for",
    "on",
    "with",
    "is",
    "are",
    "be",
    "as",
    "at",
    "by",
    "we",
    "you",
    "our",
    "your",
    "this",
    "that",
    "will",
    "have",
    "has",
    "i",
    "it",
    "from",
    "their",
    "they",
    "who",
    "what",
}

_ADVANCE_AT = 70.0
_HOLD_AT = 50.0


def _tokens(*texts: str | None) -> set[str]:
    """Keyword set. Keeps ``. + #`` *inside* tokens (node.js, c++, c#) but
    strips them from the boundaries so trailing punctuation never fragments a
    word (``postgres.`` -> ``postgres``)."""
    blob = " ".join(t for t in texts if t).lower()
    out: set[str] = set()
    for raw in re.findall(r"[a-z0-9+#.]+", blob):
        tok = raw.strip(".")
        if len(tok) >= 3 and tok not in _STOPWORDS:
            out.add(tok)
    return out


def _recommendation(score: float) -> str:
    if score >= _ADVANCE_AT:
        return "advance"
    if score >= _HOLD_AT:
        return "hold"
    return "reject"


class Scorer(Protocol):
    async def score(
        self, *, job: dict[str, Any], application: dict[str, Any], candidate: dict[str, Any]
    ) -> ScoreResult: ...


class HeuristicScorer:
    """Deterministic: how well does the candidate's material match the job?"""

    async def score(
        self, *, job: dict[str, Any], application: dict[str, Any], candidate: dict[str, Any]
    ) -> ScoreResult:
        job_tokens = _tokens(job.get("title"), job.get("description"), job.get("requirements"))
        cand_tokens = _tokens(
            application.get("cover_letter"),
            candidate.get("full_name"),
            candidate.get("source"),
            job.get("seniority"),
        )
        risk_flags: list[str] = []
        if not application.get("cover_letter"):
            risk_flags.append("no_cover_letter")
        if not application.get("cv_file_url"):
            risk_flags.append("no_cv")
        if not candidate.get("email"):
            risk_flags.append("no_contact_email")

        if not job_tokens:
            overlap = 0.0
        else:
            overlap = len(job_tokens & cand_tokens) / len(job_tokens)

        # Base 35, up to +60 for keyword coverage, minus 7 per risk flag.
        score = 35.0 + overlap * 60.0 - 7.0 * len(risk_flags)
        score = round(max(0.0, min(100.0, score)), 1)
        summary = (
            f"Heuristic match: {int(overlap * 100)}% of role keywords present in the "
            f"candidate's material; {len(risk_flags)} data gap(s)."
        )
        return ScoreResult(
            score=score,
            summary=summary,
            risk_flags=risk_flags,
            recommendation=_recommendation(score),
            method="heuristic",
        )


class LLMScorer:
    """Claude-backed scorer with a heuristic safety net."""

    _SYSTEM = (
        "You are a hiring screening assistant. Score how well a candidate fits a "
        "role from 0-100 and respond ONLY with a JSON object with keys: "
        '"score" (number 0-100), "summary" (string, <=400 chars), '
        '"risk_flags" (array of short strings), "recommendation" '
        '(one of "advance", "hold", "reject"). Be fair and avoid bias on '
        "protected characteristics."
    )

    def __init__(self, *, api_key: str, model: str) -> None:
        from libs.llm.client import AnthropicClient

        self._client = AnthropicClient(model=model, api_key=api_key)
        self._fallback = HeuristicScorer()

    @staticmethod
    def _prompt(job: dict[str, Any], application: dict[str, Any], candidate: dict[str, Any]) -> str:
        return (
            f"ROLE\nTitle: {job.get('title')}\nSeniority: {job.get('seniority')}\n"
            f"Description: {job.get('description')}\n"
            f"Requirements: {job.get('requirements')}\n\n"
            f"CANDIDATE\nName: {candidate.get('full_name')}\n"
            f"Country: {candidate.get('country')}\nSource: {candidate.get('source')}\n"
            f"Cover letter: {application.get('cover_letter')}\n"
            f"CV on file: {bool(application.get('cv_file_url'))}\n\n"
            "Return the JSON object now."
        )

    async def score(
        self, *, job: dict[str, Any], application: dict[str, Any], candidate: dict[str, Any]
    ) -> ScoreResult:
        prompt = f"{self._SYSTEM}\n\n{self._prompt(job, application, candidate)}"
        try:
            raw = await self._client.chat_json(prompt)
            return ScoreResult(
                score=float(max(0.0, min(100.0, float(raw["score"])))),
                summary=str(raw.get("summary", "")).strip()[:400],
                risk_flags=[str(f) for f in raw.get("risk_flags", []) if str(f).strip()],
                recommendation=str(
                    raw.get("recommendation") or _recommendation(float(raw["score"]))
                ),
                method="llm",
            )
        except Exception:  # noqa: BLE001 - any model/parse failure -> heuristic
            logger.warning("LLM scoring failed; falling back to heuristic", exc_info=True)
            result = await self._fallback.score(
                job=job, application=application, candidate=candidate
            )
            result.risk_flags = [*result.risk_flags, "llm_unavailable"]
            return result


def build_scorer(*, api_key: str | None, model: str) -> Scorer:
    if api_key:
        logger.info("AI scoring: using Claude model %s", model)
        return LLMScorer(api_key=api_key, model=model)
    logger.info("AI scoring: ANTHROPIC_API_KEY not set, using heuristic scorer")
    return HeuristicScorer()
