# AI Playground - Streamlit Application

A modular, well-structured Streamlit application for interacting with AI models, built following SOLID principles and Python best practices.

## 🏗️ Architecture

This application follows a clean, modular architecture based on SOLID principles:

### SOLID Principles Applied

1. **Single Responsibility Principle (SRP)**
   - Each class has one specific responsibility
   - `SessionStateManager`: Manages session state only
   - `HeaderComponent`, `ModelSelectorComponent`, etc.: Each UI component handles its own rendering
   - `PlaygroundController`: Orchestrates application flow

2. **Open/Closed Principle (OCP)**
   - The system is open for extension but closed for modification
   - New AI services can be added without modifying existing code
   - New UI components can be added independently

3. **Liskov Substitution Principle (LSP)**
   - `AIServiceInterface` defines a contract that all AI services follow
   - Any implementation can be substituted without breaking the application

4. **Interface Segregation Principle (ISP)**
   - Interfaces are focused and specific
   - `AIServiceInterface` provides only essential methods

5. **Dependency Inversion Principle (DIP)**
   - High-level modules depend on abstractions, not concrete implementations
   - Controller depends on `AIServiceInterface`, not specific implementations
   - `AIServiceFactory` manages the creation of concrete instances

## 📁 Project Structure

```
.
├── app.py                  # Main entry point
├── config.py              # Configuration and constants
├── models.py              # Pydantic data models
├── session_manager.py     # Session state management
├── ai_service.py          # AI service interface and implementations
├── ui_components.py       # Reusable UI components
├── controller.py          # Application controller
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## 🚀 Features

- **Model Selection**: Choose from multiple AI models (Gemini, Claude, GPT-4)
- **Dual Prompt System**: Separate system and user prompts
- **Response Display**: View AI-generated responses with metadata
- **Toggle Views**: Show/hide prompts in response section
- **Clean UI**: Modern, intuitive interface with custom styling
- **Session Management**: Persistent state across interactions
- **Reset Functionality**: Clear all inputs and responses

## 📦 Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup Steps

1. **Clone or download the project files**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   streamlit run app.py
   ```

4. **Access the application**:
   - The application will automatically open in your default browser
   - Default URL: `http://localhost:8501`

## 🎯 Usage

### Basic Workflow

1. **Select a Model**: Choose your preferred AI model from the dropdown
2. **Enter System Prompt** (optional): Provide system-level instructions
3. **Enter User Prompt**: Type your query or prompt
4. **Submit**: Click the Submit button to generate a response
5. **View Response**: See the generated response in the right panel
6. **Toggle Views**: Use "View Prompt" and "View System Prompt" buttons to show/hide prompts
7. **Reset**: Click Reset to clear all inputs and start fresh

### Example Use Cases

- **Content Generation**: Generate articles, stories, or creative content
- **Code Assistance**: Get help with coding problems
- **Question Answering**: Ask questions and get detailed answers
- **Experimentation**: Test different prompts and system instructions

## 🔧 Configuration

### Customizing Models

Edit `config.py` to add or modify available models:

```python
class AIModel(Enum):
    YOUR_MODEL = "Your Model Name"
```

### Customizing UI

Modify `config.py` to change:
- Colors and styling (`StyleConfig`)
- Button labels and text (`UIConfig`)
- Default settings (`AppConfig`)

### Adding Real AI Integrations

To integrate with real AI APIs:

1. Create a new class in `ai_service.py` that implements `AIServiceInterface`
2. Add API credentials handling
3. Implement the `generate_response()` method
4. Update `AIServiceFactory` to route to your implementation

Example:
```python
class OpenAIService(AIServiceInterface):
    def __init__(self, model_name: str):
        self._model_name = model_name
        # Initialize OpenAI client
    
    def generate_response(self, prompt_data: PromptData) -> ModelResponse:
        # Call OpenAI API
        pass
```

## 🧪 Testing

The application uses a mock AI service (`MockAIService`) for demonstration purposes. This allows you to:
- Test the UI without API keys
- Develop and debug without API costs
- Understand the expected behavior

## 📝 Code Style

The codebase follows Python best practices:

- **Naming Conventions**:
  - Classes: `PascalCase`
  - Functions/Methods: `snake_case`
  - Constants: `UPPER_SNAKE_CASE`
  - Private methods: `_leading_underscore`

- **Documentation**:
  - Comprehensive docstrings for all modules, classes, and methods
  - Type hints throughout the codebase
  - Clear inline comments where needed

- **Organization**:
  - Logical separation of concerns
  - Modular design for easy maintenance
  - Minimal coupling between components

## 🔐 Security Considerations

When deploying to production:

1. **API Keys**: Store API keys in environment variables, not in code
2. **Input Validation**: Validate all user inputs (already implemented with Pydantic)
3. **Rate Limiting**: Implement rate limiting for API calls
4. **Error Handling**: Add comprehensive error handling for production use

## 🚧 Future Enhancements

Potential improvements:
- Add user authentication
- Implement conversation history
- Add file upload support
- Include image generation capabilities
- Add export functionality for responses
- Implement streaming responses
- Add model comparison feature
- Include token usage tracking and limits

## 📄 License

This project is provided as-is for educational and demonstration purposes.

## 🤝 Contributing

To contribute:
1. Follow the existing code structure
2. Maintain SOLID principles
3. Add docstrings for new code
4. Test thoroughly before submitting

## 📧 Support

For issues or questions, please refer to the Streamlit documentation: https://docs.streamlit.io

---

**Built with ❤️ using Streamlit and Python**
