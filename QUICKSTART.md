# Quick Start Guide - AI Playground Development

## 🚀 Get Started in 5 Minutes

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Run the Application

**Linux/Mac**:
```bash
./run.sh
```

**Windows**:
```bash
run.bat
```

**Or manually**:
```bash
streamlit run app.py
```

### Step 3: Open in Browser

Navigate to: `http://localhost:8501`

## 🛠️ Development Workflow

### Adding a New AI Service

**1. Create the service class** in `ai_service.py`:

```python
class YourAIService(AIServiceInterface):
    """Your custom AI service implementation."""
    
    def __init__(self, model_name: str):
        self._model_name = model_name
        self._api_key = os.getenv('YOUR_API_KEY')
        # Initialize your API client
    
    def generate_response(self, prompt_data: PromptData) -> ModelResponse:
        """Generate response using your API."""
        try:
            # Call your API
            response_text = self._call_api(prompt_data)
            
            return ModelResponse(
                model_name=self._model_name,
                response_text=response_text,
                timestamp=datetime.now(),
                tokens_used=len(response_text.split())
            )
        except Exception as e:
            raise RuntimeError(f"API call failed: {str(e)}")
    
    def get_model_name(self) -> str:
        return self._model_name
    
    def _call_api(self, prompt_data: PromptData) -> str:
        # Your API logic here
        pass
```

**2. Update the factory** in `ai_service.py`:

```python
class AIServiceFactory:
    @staticmethod
    def create_service(model_name: str) -> AIServiceInterface:
        if model_name == "Your Model":
            return YourAIService(model_name)
        # ... existing models
        return MockAIService(model_name)
```

**3. Add to config** in `config.py`:

```python
class AIModel(Enum):
    YOUR_MODEL = "Your Model"
    # ... existing models
```

That's it! Your new service is now integrated.

### Adding a New UI Component

**1. Create component class** in `ui_components.py`:

```python
class YourComponent:
    """Your custom component description."""
    
    @staticmethod
    def render(data: Any, callback: Callable) -> None:
        """
        Render your component.
        
        Args:
            data: Data to display
            callback: Function to call on interaction
        """
        st.markdown("**Your Component**")
        
        # Your Streamlit UI code here
        user_input = st.text_input("Label", value=data)
        
        if st.button("Action"):
            callback(user_input)
```

**2. Use in controller** in `controller.py`:

```python
def run(self):
    # ... existing code
    
    # Add your component
    YourComponent.render(
        data=self._session_manager.get_some_data(),
        callback=self._on_some_action
    )
```

### Adding Configuration Options

**Edit `config.py`**:

```python
class AppConfig:
    # Add your settings
    NEW_FEATURE_ENABLED = True
    MAX_ITEMS = 10
    CUSTOM_SETTING = "value"
```

**Use in code**:

```python
from config import AppConfig

if AppConfig.NEW_FEATURE_ENABLED:
    # Your feature code
    pass
```

## 🧪 Testing Your Changes

### Manual Testing

1. Run the app: `streamlit run app.py`
2. Test in browser
3. Check console for errors

### Unit Testing (Example)

Create `test_your_feature.py`:

```python
import pytest
from your_module import YourClass

def test_your_function():
    """Test your function."""
    result = YourClass().your_method("input")
    assert result == "expected_output"

def test_error_handling():
    """Test error cases."""
    with pytest.raises(ValueError):
        YourClass().your_method(None)
```

Run tests:
```bash
pytest test_your_feature.py
```

## 🎨 Customizing the UI

### Changing Colors

**Edit `config.py`**:

```python
class StyleConfig:
    PRIMARY_COLOR = "#FF6B35"      # Main accent color
    SECONDARY_COLOR = "#4ECDC4"    # Secondary accent
    BACKGROUND_COLOR = "#F7F7F7"   # Background
    TEXT_COLOR = "#2C3E50"         # Text color
```

### Adding Custom CSS

**Edit `config.py`**:

```python
class StyleConfig:
    CUSTOM_CSS = """
    <style>
    /* Your custom CSS */
    .your-class {
        color: red;
        font-size: 16px;
    }
    </style>
    """
```

### Changing Layout

**Edit `controller.py`**:

```python
def run(self):
    # Change column ratio [left, right]
    left_col, right_col = st.columns([1, 2])  # Right is 2x wider
    
    # Or use different layouts
    col1, col2, col3 = st.columns(3)  # Three equal columns
```

## 🔧 Common Development Tasks

### Adding a New Session State Variable

**1. In `session_manager.py`**:

```python
def _initialize_state(self) -> None:
    # ... existing code
    if "your_variable" not in st.session_state:
        st.session_state.your_variable = "default_value"

def get_your_variable(self) -> str:
    return st.session_state.your_variable

def set_your_variable(self, value: str) -> None:
    st.session_state.your_variable = value
```

### Adding a New Event Handler

**In `controller.py`**:

```python
def _on_your_action(self, data: Any) -> None:
    """
    Handle your custom action.
    
    Args:
        data: Data from the action
    """
    # Process the action
    result = self._process(data)
    
    # Update state
    self._session_manager.set_something(result)
    
    # Show feedback
    st.success("Action completed!")
```

### Adding Validation

**Using Pydantic in `models.py`**:

```python
from pydantic import BaseModel, validator

class YourModel(BaseModel):
    field: str
    
    @validator('field')
    def validate_field(cls, value: str) -> str:
        if not value:
            raise ValueError("Field cannot be empty")
        if len(value) > 100:
            raise ValueError("Field too long")
        return value
```

## 📝 Code Checklist

Before committing changes:

- [ ] Code follows naming conventions
- [ ] All functions have docstrings
- [ ] Type hints are added
- [ ] No hardcoded values (use config)
- [ ] Error handling is implemented
- [ ] Tested manually
- [ ] No debug print statements
- [ ] Comments explain "why", not "what"

## 🐛 Debugging Tips

### Enable Streamlit Debug Mode

```bash
streamlit run app.py --logger.level=debug
```

### Add Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.error("Error message")
```

### Check Session State

```python
# Add to your controller
st.sidebar.write("Debug Info")
st.sidebar.json(dict(st.session_state))
```

### Common Issues

**Issue**: Changes not showing
- **Solution**: Hard refresh browser (Ctrl+F5)

**Issue**: Import errors
- **Solution**: Check Python path and file names

**Issue**: Session state not persisting
- **Solution**: Ensure `st.rerun()` is called after changes

## 🚢 Deployment

### Local Development

```bash
streamlit run app.py
```

### Streamlit Cloud

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect repository
4. Deploy!

### Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py"]
```

Build and run:
```bash
docker build -t ai-playground .
docker run -p 8501:8501 ai-playground
```

## 📚 Learning Resources

### Streamlit Basics
- [Streamlit Docs](https://docs.streamlit.io)
- [Streamlit Gallery](https://streamlit.io/gallery)
- [Streamlit Cheat Sheet](https://docs.streamlit.io/library/cheatsheet)

### Python Best Practices
- [PEP 8 Style Guide](https://pep8.org/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Clean Code Principles](https://gist.github.com/wojteklu/73c6914cc446146b8b533c0988cf8d29)

### SOLID Principles
- [SOLID Made Simple](https://www.digitalocean.com/community/conceptual_articles/s-o-l-i-d-the-first-five-principles-of-object-oriented-design)
- [Real Python: SOLID](https://realpython.com/solid-principles-python/)

## 💡 Pro Tips

1. **Use Streamlit Caching**: For expensive operations
   ```python
   @st.cache_data
   def expensive_function():
       # Your code
       pass
   ```

2. **Session State Keys**: Always use unique keys
   ```python
   st.button("Click", key="unique_key_123")
   ```

3. **Layout Control**: Use columns and containers
   ```python
   with st.container():
       st.write("Grouped content")
   ```

4. **Progress Indicators**: Show feedback
   ```python
   with st.spinner("Processing..."):
       # Your code
       pass
   ```

5. **Error Handling**: Always catch exceptions
   ```python
   try:
       # Your code
   except Exception as e:
       st.error(f"Error: {str(e)}")
   ```

## 🤝 Need Help?

- Check `ARCHITECTURE.md` for detailed design docs
- Read `README.md` for overview
- Review code comments and docstrings
- Streamlit [Community Forum](https://discuss.streamlit.io/)

---

**Happy Coding! 🎉**
