# AI Playground - Project Structure

```
ai-playground/
│
├── 📄 app.py                    # Main application entry point
│   └── Configures Streamlit page
│   └── Initializes and runs controller
│
├── ⚙️ config.py                 # Configuration and constants
│   ├── AIModel (Enum)           # Available AI models
│   ├── UIConfig                 # UI-related settings
│   ├── StyleConfig              # CSS styling configuration
│   └── AppConfig                # General app settings
│
├── 📊 models.py                 # Data models (Pydantic)
│   ├── PromptData               # Prompt data structure
│   ├── ModelResponse            # AI response structure
│   └── UIState                  # UI state representation
│
├── 💾 session_manager.py        # Session state management
│   └── SessionStateManager      # Manages Streamlit session state
│       ├── Initialize state
│       ├── Getters/Setters
│       └── Reset operations
│
├── 🤖 ai_service.py             # AI service layer
│   ├── AIServiceInterface       # Abstract interface
│   ├── MockAIService            # Mock implementation
│   └── AIServiceFactory         # Service factory
│
├── 🎨 ui_components.py          # Reusable UI components
│   ├── HeaderComponent          # App header with navigation
│   ├── ModelSelectorComponent   # Model selection dropdown
│   ├── PromptInputComponent     # Prompt input areas
│   ├── ActionButtonsComponent   # Reset and Submit buttons
│   ├── ResponseDisplayComponent # Response display with toggles
│   └── StyleComponent           # CSS injection
│
├── 🎮 controller.py             # Application controller (MVC)
│   └── PlaygroundController     # Main controller
│       ├── Coordinates components
│       ├── Handles user events
│       └── Manages app flow
│
├── 📦 requirements.txt          # Python dependencies
│   ├── streamlit
│   ├── pydantic
│   └── python-dateutil
│
├── 🚀 run.sh                    # Linux/Mac startup script
├── 🚀 run.bat                   # Windows startup script
│
├── 📖 README.md                 # Project overview and guide
├── 🏛️ ARCHITECTURE.md           # Detailed architecture docs
├── 🏃 QUICKSTART.md             # Quick development guide
├── 📋 PROJECT_STRUCTURE.md      # This file
│
└── 🙈 .gitignore                # Git ignore patterns

```

## 🔗 Component Dependencies

```
app.py
  └── controller.py
      ├── session_manager.py
      │   └── models.py
      ├── ai_service.py
      │   └── models.py
      ├── ui_components.py
      │   └── config.py
      └── config.py

All components follow SOLID principles with minimal coupling
```

## 📊 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        User Interface                        │
│                      (ui_components.py)                      │
└────────────────┬───────────────────────────┬─────────────────┘
                 │                           │
                 ▼                           ▼
         ┌───────────────┐          ┌──────────────┐
         │  Controller   │          │   Session    │
         │ (controller)  │◄────────►│   Manager    │
         └───────┬───────┘          └──────────────┘
                 │
                 ▼
         ┌──────────────┐
         │  AI Service  │
         │  (Factory)   │
         └──────┬───────┘
                │
                ▼
         ┌──────────────┐
         │ AI Providers │
         │ (Mock/Real)  │
         └──────────────┘
```

## 🏗️ Architecture Layers

```
┌─────────────────────────────────────────┐
│         Presentation Layer              │  ← UI Components
│     (Streamlit UI Components)           │
├─────────────────────────────────────────┤
│        Application Layer                │  ← Controller
│    (Business Logic Orchestration)       │
├─────────────────────────────────────────┤
│         Service Layer                   │  ← AI Services
│    (AI Integration & Processing)        │
├─────────────────────────────────────────┤
│          Data Layer                     │  ← Models & State
│   (Data Models & Session Management)    │
└─────────────────────────────────────────┘
```

## 🎯 SOLID Principles Mapping

| Principle | Implementation | Location |
|-----------|----------------|----------|
| **S**ingle Responsibility | Each class has one job | All modules |
| **O**pen/Closed | Extend via interfaces | ai_service.py |
| **L**iskov Substitution | Interface implementations | AIServiceInterface |
| **I**nterface Segregation | Focused interfaces | AIServiceInterface |
| **D**ependency Inversion | Depend on abstractions | controller.py |

## 🔄 Key Workflows

### 1. Application Startup
```
app.py
  → configure_page()
  → create_controller()
  → controller.run()
    → Initialize components
    → Render UI
```

### 2. User Submits Prompt
```
User clicks Submit
  → ActionButtonsComponent detects
  → Calls controller._on_submit()
  → Retrieves prompts from SessionStateManager
  → Creates PromptData (validated)
  → Calls ai_service.generate_response()
  → Adds response to session
  → UI rerenders
```

### 3. Adding New AI Model
```
1. Add to AIModel enum (config.py)
2. Create Service class (ai_service.py)
3. Update AIServiceFactory
4. Done! No other changes needed
```

## 📁 File Responsibilities

| File | Lines | Purpose | Key Classes |
|------|-------|---------|-------------|
| app.py | ~35 | Entry point | main() |
| config.py | ~80 | Configuration | AIModel, UIConfig, StyleConfig |
| models.py | ~60 | Data structures | PromptData, ModelResponse |
| session_manager.py | ~120 | State management | SessionStateManager |
| ai_service.py | ~130 | AI integration | AIServiceInterface, MockAIService |
| ui_components.py | ~240 | UI rendering | Multiple component classes |
| controller.py | ~170 | App orchestration | PlaygroundController |

## 🧩 Component Interaction Matrix

|  | session_manager | ai_service | ui_components | config |
|--|----------------|------------|---------------|--------|
| **controller** | ✅ Read/Write | ✅ Calls | ✅ Renders | ✅ Uses |
| **ui_components** | ❌ No access | ❌ No access | - | ✅ Uses |
| **ai_service** | ❌ No access | - | ❌ No access | ✅ Uses |
| **session_manager** | - | ❌ No access | ❌ No access | ✅ Uses |

✅ = Has access/dependency  
❌ = No access (loose coupling)

## 🎨 UI Component Hierarchy

```
PlaygroundController.run()
│
├── StyleComponent.inject_styles()
├── HeaderComponent.render()
│   ├── Title
│   ├── Documentation button
│   └── Engage button
│
├── Left Column
│   ├── ModelSelectorComponent.render()
│   ├── PromptInputComponent.render_system_prompt()
│   ├── PromptInputComponent.render_user_prompt()
│   └── ActionButtonsComponent.render()
│       ├── Reset button
│       └── Submit button
│
└── Right Column
    └── ResponseDisplayComponent.render()
        ├── Response list
        ├── Toggle buttons
        └── Response metadata
```

## 🔐 Security Layers

```
Input Validation
  ↓
Pydantic Models (models.py)
  ↓
Business Logic (controller.py)
  ↓
API Service (ai_service.py)
  ↓
External API Call
```

## 📈 Extensibility Points

### Easy to Extend
- ✅ Add new AI models
- ✅ Add new UI components
- ✅ Add new configuration options
- ✅ Add new event handlers

### Requires More Work
- ⚠️ Change data models (affects multiple layers)
- ⚠️ Modify session state structure
- ⚠️ Change overall UI layout

## 🧪 Testing Structure

```
tests/
├── unit/
│   ├── test_session_manager.py
│   ├── test_ai_service.py
│   ├── test_models.py
│   └── test_controller.py
│
├── integration/
│   ├── test_controller_flow.py
│   └── test_ui_interactions.py
│
└── e2e/
    └── test_app.py
```

## 📦 Deployment Structure

```
Production
├── app.py + components
├── requirements.txt
├── .streamlit/
│   └── config.toml
├── secrets.toml (for API keys)
└── .env (environment variables)
```

## 🎓 Learning Path

1. **Beginner**: Start with `app.py` → `config.py`
2. **Intermediate**: Explore `controller.py` → `ui_components.py`
3. **Advanced**: Deep dive into `ai_service.py` → `models.py`
4. **Expert**: Read `ARCHITECTURE.md` for design patterns

## 📝 Notes

- All Python files use type hints
- All classes and functions have docstrings
- Naming follows PEP 8 conventions
- Code is formatted for readability
- Comments explain "why", not "what"

---

**Total Lines of Code**: ~835  
**Total Files**: 14  
**Complexity**: Moderate  
**Maintainability**: High  
**Test Coverage**: Extensible  

---

For detailed explanations, see:
- `README.md` - Overview and installation
- `ARCHITECTURE.md` - Design decisions and patterns
- `QUICKSTART.md` - Development guide
