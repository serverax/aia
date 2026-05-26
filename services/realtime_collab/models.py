from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class OperationType(str, Enum):
    replace = "replace"
    insert = "insert"
    delete = "delete"


class CollaborationOperation(BaseModel):
    operation_id: str = Field(..., min_length=1)
    client_id: str = Field(..., min_length=1)
    base_version: int = Field(..., ge=0)
    operation: OperationType
    position: int = Field(0, ge=0)
    length: int = Field(0, ge=0)
    text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("text")
    @classmethod
    def text_required_for_insert_or_replace(cls, value: str, info: Any) -> str:
        operation = info.data.get("operation")
        if operation in {OperationType.insert, OperationType.replace} and value == "":
            raise ValueError("text is required for insert and replace operations")
        return value


class CollaborationEvent(BaseModel):
    type: Literal["snapshot", "operation_applied", "conflict", "presence", "error"]
    document_id: str
    version: int
    client_id: str | None = None
    content: str | None = None
    operation: CollaborationOperation | None = None
    message: str | None = None
    active_clients: list[str] = Field(default_factory=list)


class DocumentSnapshot(BaseModel):
    document_id: str
    version: int
    content: str
    active_clients: list[str] = Field(default_factory=list)


class ApplyOperationResponse(BaseModel):
    accepted: bool
    snapshot: DocumentSnapshot
    event: CollaborationEvent
