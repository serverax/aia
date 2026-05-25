import re
from typing import Any, Dict, List


class CitationTracker:
    def __init__(self):
        # Regex to find [CITATION: source_id]
        self.citation_pattern = re.compile(r"\[CITATION:\s*(.*?)\]")

    def extract_citations(self, text: str) -> List[str]:
        """Extract citation IDs from the text."""
        return self.citation_pattern.findall(text)

    def validate_citations(
        self, citations: List[str], retrieved_docs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate that cited IDs exist in the retrieved documents."""
        retrieved_ids = {doc.get("id") for doc in retrieved_docs}
        valid = []
        invalid = []

        for cit in citations:
            if cit in retrieved_ids:
                valid.append(cit)
            else:
                invalid.append(cit)

        return {"valid": valid, "invalid": invalid, "all_valid": len(invalid) == 0}

    def format_citation(self, doc: Dict[str, Any], style: str = "APA") -> str:
        """Format a document as a citation string."""
        # Simple placeholder formatting
        regulation = doc.get("regulation", "Unknown Regulation")
        section = doc.get("section", "Unknown Section")
        source = doc.get("source", "")

        if style == "APA":
            return f"{regulation}. {section}. Retrieved from {source}"
        return f"{regulation}, {section} ({source})"
