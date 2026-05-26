"""Unit tests for the deterministic heuristic scorer."""

from __future__ import annotations

from apps.api.scoring import HeuristicScorer, _recommendation


async def test_strong_match_scores_high_and_advances():
    scorer = HeuristicScorer()
    job = {
        "title": "Python Engineer",
        "description": "python fastapi postgres async services",
        "requirements": "python fastapi postgres async kubernetes docker",
    }
    application = {
        "cover_letter": "python fastapi postgres async kubernetes docker expert",
        "cv_file_url": "https://cv.example/jane.pdf",
    }
    candidate = {"full_name": "Jane", "email": "jane@example.com"}

    result = await scorer.score(job=job, application=application, candidate=candidate)
    assert result.method == "heuristic"
    assert result.score >= 70
    assert result.recommendation == "advance"
    assert result.risk_flags == []


async def test_missing_data_flags_and_lowers_score():
    scorer = HeuristicScorer()
    job = {"title": "Designer", "description": "figma branding", "requirements": "figma"}
    application = {"cover_letter": None, "cv_file_url": None}
    candidate = {"full_name": "No Contact", "email": None}

    result = await scorer.score(job=job, application=application, candidate=candidate)
    assert set(result.risk_flags) == {"no_cover_letter", "no_cv", "no_contact_email"}
    assert result.score < 70


async def test_scoring_is_deterministic():
    scorer = HeuristicScorer()
    job = {"title": "X", "description": "alpha beta gamma", "requirements": "alpha beta"}
    application = {"cover_letter": "alpha beta", "cv_file_url": "u"}
    candidate = {"email": "a@b.com"}
    first = await scorer.score(job=job, application=application, candidate=candidate)
    second = await scorer.score(job=job, application=application, candidate=candidate)
    assert first.model_dump() == second.model_dump()


def test_recommendation_thresholds():
    assert _recommendation(95) == "advance"
    assert _recommendation(70) == "advance"
    assert _recommendation(69.9) == "hold"
    assert _recommendation(50) == "hold"
    assert _recommendation(49.9) == "reject"
