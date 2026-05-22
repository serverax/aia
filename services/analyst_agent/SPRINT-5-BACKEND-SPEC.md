# SPRINT 5: EDITOR & DOCUMENT FINALIZATION — BACKEND SPECIFICATION

## Objective
Implement the backend foundation for the Editor Agent, focusing on high-fidelity document generation (DOCX/PDF), audit retention of intermediate drafts, and bulk decision export capabilities.

## 1. Data Models (`models/finalizer.py`)

### `DocumentDraft`
- `draft_id`: Unique identifier for the draft.
- `agent_id`: Agent that produced the content.
- `raw_content`: The original LLM output.
- `formatted_content`: Content after Editor Agent formatting.
- `version`: Incremental version number.
- `timestamp`: Creation time.

### `FinalDocument`
- `document_id`: Unique ID.
- `project_id`: Link to the parent project.
- `format`: `DOCX` | `PDF`.
- `s3_url`: Location of the stored file.
- `audit_trail`: List of `draft_id`s used to compile this document.

## 2. API Endpoints (`analyst_service.py` extensions)

### `POST /analyst/document/finalize`
- **Input**: `project_id`, `template_id`, `format`.
- **Action**: Editor Agent retrieves all recommendations and findings for the project, applies the selected template, and generates a formatted document.
- **Output**: `document_id`, `s3_url`.

### `GET /analyst/document/audit/{document_id}`
- **Action**: Retrieve the full history of drafts and evidence used for a finalized document.
- **Output**: List of `DocumentDraft` objects.

### `POST /analyst/export/bulk`
- **Input**: List of `project_ids`, `format`.
- **Action**: Compile a summary report of all selected projects.
- **Output**: Download URL for the zip/combined file.

## 3. Integration Points

### Cursor Sprint 5 UI
- **Document Preview**: UI calls a new `/analyst/document/preview` endpoint (HTML snippet) to show how the draft looks before final PDF generation.
- **Manual Overrides**: UI allows users to edit `raw_content`. The backend must support `POST /analyst/document/draft/update`.

### Audit Layer
- Every finalized document must be cryptographically signed (referencing Sprint 6 security requirement).

## 4. Performance Requirements
- **DOCX Generation**: < 2 seconds for a 10-page report.
- **PDF Generation**: < 5 seconds.
- **Audit Retrieval**: < 500ms.
