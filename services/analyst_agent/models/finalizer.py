from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone
from enum import Enum


class DocumentFormat(str, Enum):
    DOCX = "DOCX"
    PDF = "PDF"


class StorageProvider(str, Enum):
    S3 = "S3"
    AZURE_BLOB = "AZURE_BLOB"
    LOCAL = "LOCAL"


class DocumentDraft(BaseModel):
    draft_id: UUID = Field(default_factory=uuid4)
    project_id: str
    agent_id: str
    raw_content: str  # Markdown
    formatted_content: Optional[str] = None  # HTML preview
    version: int = 1
    metadata: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FinalDocument(BaseModel):
    document_id: UUID = Field(default_factory=uuid4)
    project_id: str
    format: DocumentFormat
    storage_provider: StorageProvider = StorageProvider.LOCAL
    file_url: str
    signature_hash: str
    audit_trail: List[UUID]  # List of DocumentDraft IDs
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FinalizeRequest(BaseModel):
    project_id: str
    template_id: str = "default"
    format: DocumentFormat = DocumentFormat.PDF
    include_audit_summary: bool = True


class FinalizeResponse(BaseModel):
    document_id: UUID
    file_url: str
    generation_time_ms: int


class BulkExportRequest(BaseModel):
    project_filters: Dict[str, Any]
    format: str = "JSON"
    compression: Optional[str] = "ZIP"


class BulkExportResponse(BaseModel):
    job_id: str
    status_url: str
