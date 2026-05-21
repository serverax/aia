from typing import List, Dict, Any

class RecommendationGenerator:
    def generate(self, analysis_text: str, risk_assessment: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate 3-5 actionable recommendations based on analysis and risk.
        """
        overall_level = risk_assessment.get("overall_level", "LOW")
        factors = risk_assessment.get("factors", {})
        
        recommendations = []
        
        # Rule-based generator for MVP
        if factors.get("compliance", 0) > 0.5:
            recommendations.append({
                "priority": 1,
                "text": "Initiate immediate compliance audit for regulatory alignment.",
                "risk_level": "HIGH",
                "impact": "Reduces compliance risk by 60%",
                "timeline": "Soon",
                "effort": "Medium"
            })
            
        if factors.get("financial", 0) > 0.3:
            recommendations.append({
                "priority": 2,
                "text": "Perform a deep-dive financial health assessment.",
                "risk_level": "MEDIUM",
                "impact": "Reduces financial exposure by 30%",
                "timeline": "Soon",
                "effort": "High"
            })

        if factors.get("legal", 0) > 0.4:
            recommendations.append({
                "priority": 3,
                "text": "Review all active contracts for liability gaps.",
                "risk_level": "HIGH",
                "impact": "Mitigates legal liability by 50%",
                "timeline": "Soon",
                "effort": "Medium"
            })

        # Default recommendation if list is short
        if len(recommendations) < 3:
            recommendations.append({
                "priority": len(recommendations) + 1,
                "text": "Monitor industry trends for proactive risk management.",
                "risk_level": "LOW",
                "impact": "Increases operational resilience by 15%",
                "timeline": "Medium-term",
                "effort": "Low"
            })

        # Rank by risk level (HIGH first)
        level_map = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        recommendations.sort(key=lambda x: level_map.get(x["risk_level"], 0), reverse=True)
        
        # Reset priority after sort
        for i, rec in enumerate(recommendations):
            rec["priority"] = i + 1
            
        return recommendations[:5]
