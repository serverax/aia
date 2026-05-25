import re
from typing import List

from .schemas import ComplianceDocument


class DocumentProcessor:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def normalize_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def chunk_document(self, doc: ComplianceDocument) -> List[ComplianceDocument]:
        """Split a document into smaller chunks if it's too long."""
        content = self.normalize_text(doc.content)

        if len(content) <= self.chunk_size:
            doc.content = content
            return [doc]

        chunks = []
        start = 0
        chunk_idx = 0

        while start < len(content):
            end = start + self.chunk_size
            chunk_text = content[start:end]

            # Create a new document object for the chunk
            new_doc = doc.model_copy()
            new_doc.id = f"{doc.id}_chunk_{chunk_idx}"
            new_doc.content = chunk_text
            new_doc.metadata["parent_id"] = doc.id
            new_doc.metadata["chunk_index"] = chunk_idx

            chunks.append(new_doc)

            start += self.chunk_size - self.chunk_overlap
            chunk_idx += 1

        return chunks
