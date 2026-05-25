from .schemas import ComplianceDocument

SAMPLE_DOCUMENTS = [
    ComplianceDocument(
        id="POL_001",
        type="policy",
        title="Data Privacy and Protection Policy",
        content="This policy outlines the procedures for handling personal data of EU residents in accordance with GDPR. All data must be encrypted at rest and in transit.",
        jurisdiction="EU",
        risk_category="Compliance",
        date="2024-01-15",
        source="Corporate Compliance Handbook",
    ),
    ComplianceDocument(
        id="POL_002",
        type="policy",
        title="Anti-Money Laundering (AML) Policy",
        content="Financial institutions must verify the identity of their clients to prevent money laundering and terrorist financing. Suspicious activities must be reported to the FCA.",
        jurisdiction="UK",
        risk_category="Financial",
        date="2023-11-20",
        source="Regulatory Authority",
    ),
    ComplianceDocument(
        id="GUI_001",
        type="guideline",
        title="Cybersecurity Best Practices for Financial Services",
        content="Implement multi-factor authentication (MFA) across all external-facing applications. Regularly conduct penetration testing and vulnerability assessments.",
        jurisdiction="GLOBAL",
        risk_category="Operational",
        date="2024-03-05",
        source="Industry Standard",
    ),
    ComplianceDocument(
        id="CAS_001",
        type="case",
        title="SEC vs. TechCorp: Failure to Disclose Data Breach",
        content="In 2022, TechCorp failed to disclose a major data breach affecting 50 million users, resulting in a $100 million fine and legal repercussions for its officers.",
        jurisdiction="US",
        risk_category="Legal",
        date="2022-08-10",
        source="Legal Archives",
    ),
    ComplianceDocument(
        id="POL_003",
        type="policy",
        title="Whistleblower Protection Policy",
        content="Employees are encouraged to report unethical behavior without fear of retaliation. Reports can be made anonymously through the designated portal.",
        jurisdiction="GLOBAL",
        risk_category="Compliance",
        date="2024-02-28",
        source="HR Policy Manual",
    ),
]

# Generate more samples to reach ~50
for i in range(45):
    SAMPLE_DOCUMENTS.append(
        ComplianceDocument(
            id=f"GEN_{i:03d}",
            type="guideline",
            title=f"General Compliance Guideline {i}",
            content=f"This is a general guideline for compliance topic {i}. It covers standard operating procedures and risk mitigation strategies.",
            jurisdiction="UK" if i % 2 == 0 else "US",
            risk_category="Operational" if i % 3 == 0 else "Legal",
            date="2024-05-21",
            source="Automated System",
        )
    )
