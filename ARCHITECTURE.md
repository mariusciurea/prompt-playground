# AI Playground - Architecture Documentation

## 📐 System Architecture Overview

This document provides a detailed explanation of the AI Playground application architecture, design decisions, and implementation details.

## 🎯 Design Philosophy

The application is built on three core principles:

1. **Modularity**: Each component can be developed, tested, and maintained independently
2. **Extensibility**: New features can be added without modifying existing code
3. **Maintainability**: Clear structure and documentation for easy understanding

## 🏛️ SOLID Principles Implementation

### 1. Single Responsibility Principle (SRP)

Each class has one, and only one, reason to change:

```
SessionStateManager → Manages Streamlit session state
AIServiceInterface → Defines AI service contract
MockAIService → Implements mock AI responses
UIComponent classes → Each handles specific UI rendering
PlaygroundController → Orchestrates application flow
```

**Benefits**:
- Easier testing (each component tested in isolation)
- Reduced coupling between components
- Changes in one area don't ripple through the system

### 2. Open/Closed Principle (OCP)

The system is open for extension, closed for modification:

**Example**: Adding a new AI service
```python
# Add new service without modifying existing code
class OpenAIService(AIServiceInterface):
    def generate_response(self, prompt_data: PromptData) -> ModelResponse:
        # Implementation
        pass

# Update factory
class AIServiceFactory:
    @staticmethod
    def create_service(model_name: str) -> AIServiceInterface:
        if model_name == "GPT-4":
            return OpenAIService(model_name)
        # ... existing code remains unchanged
```

**Benefits**:
- Add features without breaking existing functionality
- Reduced risk of introducing bugs
- Easier to maintain backward compatibility

### 3. Liskov Substitution Principle (LSP)

Any implementation of `AIServiceInterface` can be substituted without breaking the application:

```python
# All these work identically from the controller's perspective
service1 = MockAIService("Model A")
service2 = OpenAIService("Model B")
service3 = AnthropicService("Model C")

# Controller doesn't care which implementation
response = service.generate_response(prompt_data)
```

**Benefits**:
- Polymorphic behavior
- Flexible service swapping
- Easy testing with mock implementations

### 4. Interface Segregation Principle (ISP)

Interfaces are focused and specific:

```python
class AIServiceInterface(ABC):
    @abstractmethod
    def generate_response(self, prompt_data: PromptData) -> ModelResponse:
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        pass
```

**Benefits**:
- Clients aren't forced to depend on methods they don't use
- Smaller, more focused interfaces
- Easier to implement and maintain

### 5. Dependency Inversion Principle (DIP)

High-level modules depend on abstractions:

```python
class PlaygroundController:
    def __init__(self):
        # Depends on interface, not concrete implementation
        self._ai_service: AIServiceInterface = None
        
    def _initialize_ai_service(self) -> None:
        # Factory provides concrete implementation
        self._ai_service = AIServiceFactory.create_service(model_name)
```

**Benefits**:
- Loose coupling between components
- Easy to swap implementations
- Facilitates testing with mocks

## 📦 Component Architecture

### Layer 1: Configuration (`config.py`)

**Purpose**: Centralized configuration management

**Components**:
- `AIModel`: Enum for available models
- `UIConfig`: UI-related constants
- `StyleConfig`: CSS styling configuration
- `AppConfig`: Application settings

**Design Decision**: Separating configuration from logic makes it easy to:
- Change settings without touching code
- Maintain consistency across the application
- Support different environments (dev, staging, prod)

### Layer 2: Data Models (`models.py`)

**Purpose**: Type-safe data structures

**Components**:
- `PromptData`: Pydantic model for prompt validation
- `ModelResponse`: Structure for AI responses
- `UIState`: Dataclass for UI state representation

**Design Decision**: Using Pydantic provides:
- Automatic validation
- Type safety
- Clear data contracts
- Self-documenting schemas

### Layer 3: Session Management (`session_manager.py`)

**Purpose**: Streamlit session state abstraction

**Responsibilities**:
- Initialize session state
- Provide getter/setter methods
- Handle state reset operations

**Design Decision**: Abstracting session state:
- Hides Streamlit implementation details
- Makes state management testable
- Provides a clean API for state operations

### Layer 4: Business Logic (`ai_service.py`)

**Purpose**: AI service abstraction and implementation

**Components**:
- `AIServiceInterface`: Abstract base class
- `MockAIService`: Mock implementation
- `AIServiceFactory`: Factory for creating services

**Design Decision**: Factory pattern enables:
- Easy addition of new AI services
- Runtime service selection
- Centralized service creation logic

### Layer 5: UI Components (`ui_components.py`)

**Purpose**: Reusable UI building blocks

**Components**:
- `HeaderComponent`: Application header
- `ModelSelectorComponent`: Model selection
- `PromptInputComponent`: Prompt input areas
- `ActionButtonsComponent`: Action buttons
- `ResponseDisplayComponent`: Response display
- `StyleComponent`: CSS injection

**Design Decision**: Component-based architecture:
- Promotes reusability
- Simplifies testing
- Makes UI changes localized
- Follows React-like patterns

### Layer 6: Application Controller (`controller.py`)

**Purpose**: Orchestrate application flow

**Responsibilities**:
- Initialize components
- Handle user events
- Coordinate between layers
- Manage application lifecycle

**Design Decision**: MVC-like pattern:
- Separates presentation from logic
- Makes application flow explicit
- Centralizes event handling

### Layer 7: Entry Point (`app.py`)

**Purpose**: Application bootstrap

**Responsibilities**:
- Configure Streamlit
- Initialize controller
- Start application

## 🔄 Data Flow

```
User Input → UI Component → Controller → Session Manager → AI Service
                                ↓                              ↓
                          Update State                   Generate Response
                                ↓                              ↓
                          Trigger Rerun ← Response Display ← Return Response
```

### Detailed Flow Example: Submit Button

1. User clicks Submit button
2. `ActionButtonsComponent` detects click
3. Calls `controller._on_submit()`
4. Controller retrieves prompts from `SessionStateManager`
5. Creates `PromptData` object (validated by Pydantic)
6. Calls `ai_service.generate_response()`
7. Service returns `ModelResponse`
8. Controller adds response to session state
9. UI rerenders with new response

## 🧪 Testing Strategy

### Unit Testing

Each component can be tested in isolation:

```python
def test_session_manager():
    manager = SessionStateManager()
    manager.set_system_prompt("test")
    assert manager.get_system_prompt() == "test"

def test_mock_ai_service():
    service = MockAIService("Test Model")
    prompt_data = PromptData(user_prompt="Hello")
    response = service.generate_response(prompt_data)
    assert response.model_name == "Test Model"
```

### Integration Testing

Test component interactions:

```python
def test_controller_submit():
    controller = PlaygroundController()
    # Simulate user input
    # Verify response generation
    # Check state updates
```

### UI Testing

Use Streamlit's testing framework:

```python
from streamlit.testing.v1 import AppTest

def test_app():
    at = AppTest.from_file("app.py")
    at.run()
    # Test UI interactions
```

## 🚀 Extension Points

### Adding a New AI Service

1. Create new class implementing `AIServiceInterface`
2. Update `AIServiceFactory`
3. Add model to `AIModel` enum
4. No changes needed to UI or controller

### Adding a New UI Component

1. Create new component class in `ui_components.py`
2. Add render method
3. Call from controller
4. No changes needed to other components

### Adding New Features

Examples:
- **Conversation History**: Add to `SessionStateManager`
- **File Upload**: New component + controller method
- **Export Responses**: New component + service method

## 🔒 Security Considerations

### Input Validation

```python
class PromptData(BaseModel):
    @validator('user_prompt')
    def validate_prompt_length(cls, value: str) -> str:
        if len(value) > 10000:
            raise ValueError("Prompt too long")
        return value
```

### API Key Management

```python
import os

class OpenAIService(AIServiceInterface):
    def __init__(self, model_name: str):
        # Load from environment variables
        self._api_key = os.getenv('OPENAI_API_KEY')
        if not self._api_key:
            raise ValueError("API key not found")
```

### Rate Limiting

```python
from functools import lru_cache
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_requests: int, time_window: timedelta):
        self._max_requests = max_requests
        self._time_window = time_window
        self._requests = []
    
    def allow_request(self) -> bool:
        now = datetime.now()
        self._requests = [r for r in self._requests 
                         if now - r < self._time_window]
        
        if len(self._requests) < self._max_requests:
            self._requests.append(now)
            return True
        return False
```

## 📊 Performance Considerations

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_response(prompt: str, model: str) -> str:
    # Cache responses for identical prompts
    pass
```

### Lazy Loading

```python
class LazyAIService:
    def __init__(self):
        self._service = None
    
    @property
    def service(self):
        if self._service is None:
            self._service = self._initialize_service()
        return self._service
```

### Asynchronous Operations

```python
import asyncio

async def generate_response_async(self, prompt_data: PromptData):
    # Async API calls
    response = await self._api_client.generate(prompt_data)
    return response
```

## 📝 Code Style Guide

### Naming Conventions

```python
# Classes: PascalCase
class AIServiceInterface:
    pass

# Functions/Methods: snake_case
def generate_response(self):
    pass

# Constants: UPPER_SNAKE_CASE
MAX_PROMPT_LENGTH = 10000

# Private methods: _leading_underscore
def _internal_method(self):
    pass
```

### Documentation

```python
def complex_function(param1: str, param2: int) -> bool:
    """
    Brief description of function.
    
    Detailed explanation if needed.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        bool: Description of return value
        
    Raises:
        ValueError: When param1 is invalid
    """
    pass
```

## 🎨 UI/UX Decisions

### Two-Column Layout

```
┌─────────────────┬─────────────────┐
│   Input Panel   │  Response Panel │
│                 │                 │
│  - Model Select │  - Responses    │
│  - Sys Prompt   │  - View Toggles │
│  - User Prompt  │  - Metadata     │
│  - Actions      │                 │
└─────────────────┴─────────────────┘
```

**Rationale**: Separate input from output for clarity

### Progressive Disclosure

- Toggle buttons reveal prompts on demand
- Reduces visual clutter
- User controls information density

### Feedback Mechanisms

- Loading spinners during generation
- Success/error messages
- Metadata display (tokens, timestamp)

## 🔮 Future Architecture Enhancements

### Microservices Architecture

```
Frontend (Streamlit) ←→ API Gateway ←→ AI Service 1
                                    ←→ AI Service 2
                                    ←→ AI Service 3
```

### Event-Driven Architecture

```python
from typing import Callable

class EventBus:
    def __init__(self):
        self._listeners = {}
    
    def subscribe(self, event: str, callback: Callable):
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)
    
    def publish(self, event: str, data: Any):
        if event in self._listeners:
            for callback in self._listeners[event]:
                callback(data)
```

### Plugin System

```python
class PluginInterface(ABC):
    @abstractmethod
    def on_response_generated(self, response: ModelResponse):
        pass

class PluginManager:
    def __init__(self):
        self._plugins = []
    
    def register_plugin(self, plugin: PluginInterface):
        self._plugins.append(plugin)
```

## 📚 Additional Resources

- [Streamlit Documentation](https://docs.streamlit.io)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [Clean Code by Robert C. Martin](https://www.amazon.com/Clean-Code-Handbook-Software-Craftsmanship/dp/0132350882)
- [Design Patterns: Elements of Reusable Object-Oriented Software](https://en.wikipedia.org/wiki/Design_Patterns)

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-30  
**Author**: Claude AI Assistant
