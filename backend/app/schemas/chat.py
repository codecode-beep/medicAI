from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(description="user or assistant")
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    save_to_history: bool = False
    report_id: int | None = None
    file_ids: list[int] = Field(default_factory=list)


class ChatResponse(BaseModel):
    session_id: str
    message: str
    role: str = "assistant"
    metadata: dict[str, Any] | None = None


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessage]
