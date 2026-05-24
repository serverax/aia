# SPRINT 5: EDITOR & DOCUMENT FINALIZATION — REFINED BACKEND SPECIFICATION

## Objective
Implement the backend foundation for the Editor Agent, focusing on high-fidelity document generation (DOCX/PDF), audit retention of intermediate drafts, and bulk decision export capabilities.

## 1. Data Models (`models/finalizer.py`)

### `DocumentDraft`
- `draft_id`: UUID
- `project_id`: String
- `agent_id`: String
- `raw_content`: Markdown (Original LLM output)
- `formatted_content`: HTML (Preview version)
- `version`: Integer
- `metadata`: Dict[str, Any] (Agent parameters, model used)
- `timestamp`: ISO-8601 String

### `FinalDocument`
- `document_id`: UUID
- `project_id`: String
- `format`: Enum[`DOCX`, `PDF`]
- `storage_provider`: Enum[`S3`, `AZURE_BLOB`]
- `file_url`: String
- `signature_hash`: String (SHA-256 for integrity)
- `audit_trail`: List[UUID] (Pointers to `DocumentDraft` IDs)

## 2. API Contracts (FastAPI / OpenAPI)

### `POST /analyst/document/finalize`
- **Description**: Triggers the Editor Agent to compile findings into a final report.
- **Request Body**:
  ```json
  {
    "project_id": "PRJ-101",
    "template_id": "legal-report-v1",
    "format": "PDF",
    "include_audit_summary": true
  }
  ```
- **Response** (201 Created):
  ```json
  {
    "document_id": "DOC-998",
    "file_url": "https://storage.ordinoxai.com/reports/DOC-998.pdf",
    "generation_time_ms": 1450
  }
  ```

### `POST /analyst/export/bulk`
- **Description**: Asynchronous batch export for large-scale compliance audits.
- **Request Body**:
  ```json
  {
    "project_filters": {
      "jurisdiction": "EU",
      "risk_level": "HIGH",
      "start_date": "2026-01-01"
    },
    "format": "JSON",
    "compression": "ZIP"
  }
  ```
- **Response** (202 Accepted):
  ```json
  {
    "job_id": "EXPORT-772",
    "status_url": "/analyst/export/status/EXPORT-772"
  }
  ```

### `GET /analyst/document/preview`
- **Description**: Returns a sanitized HTML snippet for frontend rendering.
- **Query Params**: `project_id`, `version` (optional)
- **Response**: HTML Content + Styling metadata.

## 3. Bulk Export Data Structures

### JSON Export Schema
A nested structure containing project metadata, all decision explanations, confidence scores, and citation lists for every analyzed project.

### CSV Export Schema (Flattened)
Headers: `project_id`, `date`, `overall_risk`, `matched_policies`, `top_recommendation`, `confidence_score`, `signer_id`.

## 4. Performance & Scalability
- **Pagination**: `GET /documents` and `GET /drafts` will support `limit` and `offset` (Default: 50 items/page).
- **Background Jobs**: Bulk exports use Redis Streams to handle datasets > 1000 items without blocking the main event loop.
- **Caching**: Finalized report URLs cached in Redis for 24h to avoid redundant storage I/O.

## 5. Security & Compliance
- **Integrity**: Every generated PDF is hashed; hash stored in the Audit Chain.
- **Auth**: Endpoints require `Role: Compliance_Editor` or `Role: System_Admin`.
- **Retention**: Drafts retained for 7 years as per professional services regulatory requirements.
