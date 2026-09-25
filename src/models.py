"""Domain models for the AI Playground application."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PromptData(BaseModel):
    """A prompt (system + user) and the generation parameters to run it with."""

    model_config = ConfigDict(validate_assignment=True)

    system_prompt: str = Field(default="", description="System-level instructions")
    user_prompt: str = Field(default="", description="The user's query")
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)


class ModelResponse(BaseModel):
    """An AI model's response together with the prompt that produced it."""

    model_config = ConfigDict(validate_assignment=True)

    model_name: str
    response_text: str
    user_prompt: str = ""
    system_prompt: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)
    tokens_used: int | None = None
    latency_seconds: float | None = None
    temperature: float | None = None
