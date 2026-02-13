"""
Data models for the AI Playground application
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class PromptData(BaseModel):
    """Model representing prompt data."""
    
    system_prompt: str = Field(default="", description="System-level instructions for the AI")
    user_prompt: str = Field(default="", description="User's query or prompt")
    
    @field_validator('system_prompt', 'user_prompt')
    @classmethod
    def validate_prompt_length(cls, value: str) -> str:
        """Validate that prompts are not excessively long."""
        if len(value) > 10000:
            raise ValueError("Prompt exceeds maximum length of 10000 characters")
        return value

    class Config:
        """Pydantic model configuration"""
        validate_assignment = True


class ModelResponse(BaseModel):
    """Model representing an AI model's response."""

    model_name: str = Field(..., description="Name of the AI model")
    response_text: str = Field(..., description="The generated response")
    user_prompt: str = Field(default="", description="The user prompt that generated this response")
    system_prompt: str = Field(default="", description="The system prompt used for this response")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    tokens_used: Optional[int] = Field(None, description="Number of tokens used")
    
    class Config:
        """Pydantic model configuration"""
        validate_assignment = True


@dataclass
class UIState:
    """Represents the current state of the UI."""
    
    current_model: str
    system_prompt: str
    user_prompt: str
    responses: List[ModelResponse]
    show_system_prompt: bool = False
    show_user_prompt: bool = False
    
    def reset(self) -> None:
        """Reset the UI state to defaults."""
        self.system_prompt = ""
        self.user_prompt = ""
        self.responses.clear()
        self.show_system_prompt = False
        self.show_user_prompt = False
