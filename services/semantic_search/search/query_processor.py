import re
from typing import List


class QueryProcessor:
    def __init__(self):
        # Basic synonym mapping for demonstration
        self.synonyms = {
            "gdpr": ["data privacy", "privacy protection", "eu regulation"],
            "aml": ["anti-money laundering", "financial crime", "money laundering"],
            "mfa": ["multi-factor authentication", "2fa", "two-factor authentication"],
            "breach": ["violation", "incident", "leak"],
        }

    def normalize(self, query: str) -> str:
        """Clean and normalize the search query."""
        query = query.lower()
        query = re.sub(r"[^\w\s]", "", query)
        query = re.sub(r"\s+", " ", query).strip()
        return query

    def expand_query(self, query: str) -> str:
        """Expand query with synonyms for better semantic coverage."""
        normalized = self.normalize(query)
        words = normalized.split()
        expanded = set(words)

        for word in words:
            if word in self.synonyms:
                expanded.update(self.synonyms[word])

        return " ".join(list(expanded))
