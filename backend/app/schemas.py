from typing import Any
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(min_length=1, max_length=128)

class ChatResponse(BaseModel):
    narration: str
    chart: dict[str, Any] | None = None
    recommendation: str | None = None
    mode: str
    sources: list[str]
