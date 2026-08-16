from enum import StrEnum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class LLMProvider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    AUTO = "auto"


class MessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Priority(StrEnum):
    QUALITY = "quality"
    COST = "cost"
    BALANCED = "balanced"


class Message(BaseModel):
    role: MessageRole
    content: str


class LLMRequest(BaseModel):
    messages: List[Message] = Field(min_length=1)

    provider: LLMProvider = LLMProvider.AUTO
    model: Optional[str] = None
    priority: Priority = Priority.BALANCED

    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMResponse(BaseModel):
    content: str
    provider: LLMProvider
    model: str
    usage: Optional[UsageInfo] = None
    latency_ms: int


class ProviderHealth(BaseModel):
    available: bool
    model: str
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    providers: Dict[str, ProviderHealth]
