import re
from typing import Any, Dict, List


class RiskAnalyzer:
    def __init__(self):
        self.risk_factors = {
            "financial": ["loss", "default", "bankruptcy", "fraud", "debt", "leverage"],
            "legal": ["compliance", "violation", "liability", "lawsuit", "breach", "dispute"],
            "operational": ["downtime", "failure", "delay", "disruption", "capacity", "outage"],
            "compliance": ["gdpr", "fca", "aml", "audit", "standard", "enforcement"],
        }

    def assess(self, analysis_text: str, citations: List[str] = None) -> Dict[str, Any]:
        """
        Assess risk across 4 dimensions based on keyword occurrences.
        """
        text_lower = analysis_text.lower()
        scores = {}

        for dimension, keywords in self.risk_factors.items():
            count = 0
            for keyword in keywords:
                # Use word boundaries to avoid partial matches
                count += len(re.findall(r"\b" + re.escape(keyword) + r"\b", text_lower))

            # Simple scoring: Normalize to 0-1 range (cap at 5 occurrences for max risk)
            score = min(count / 5.0, 1.0)
            scores[dimension] = score

        overall_score = sum(scores.values()) / len(scores)

        if overall_score < 0.3:
            level = "LOW"
        elif overall_score < 0.7:
            level = "MEDIUM"
        else:
            level = "HIGH"

        return {
            "overall_level": level,
            "overall_score": round(overall_score, 2),
            "factors": {k: round(v, 2) for k, v in scores.items()},
            "mitigation_needed": overall_score > 0.5,
        }
