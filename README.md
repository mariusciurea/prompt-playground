# AI Playground

A Streamlit app for learning prompt engineering with Google Gemini.

| Page | What it does |
| --- | --- |
| **Playground** | Write a system + user prompt, tune the temperature, watch the answer stream in, export the session. Ready-made examples included. |
| **Engage** | Prompt-injection game: talk the model into revealing a password hidden in its system prompt. Progress is tracked per level. |
| **Reservation** | Chat with a Google ADK agent that can list/book movies and read stored data. The tools it calls are shown under each answer. |
| **Documentation** | Short in-app guide with a link to the Prompting Guide. |

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
copy .env.example .env            # then set GEMINI_API_KEY
streamlit run app.py
```

Or run `run.bat` / `run.sh`. With Docker:

```bash
docker build -t ai-playground .
docker run -p 8501:8501 --env-file .env ai-playground
```

## Configuration

Settings are validated by [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
in [src/config.py](src/config.py). They are read from environment variables or `.env`
(see [.env.example](.env.example)):

| Variable | Default | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | – (required) | Google AI Studio key |
| `GEMINI_MODEL_ID` | `gemini-3-flash-preview` | Model for Playground / Engage |
| `GEMINI_MODEL_NAME` | `Gemini 3` | Name shown in the UI |
| `AGENT_MODEL_ID` | `gemini-3.5-flash` | Model for the Reservation agent |
| `MAX_PROMPT_LENGTH` | `10000` | Max characters per prompt field |
| `DEFAULT_TEMPERATURE` | `1.0` | Initial temperature slider value |
| `LOG_LEVEL` | `INFO` | Python logging level |

## Project layout

```
app.py                    Entry point: page config, styles, st.navigation
src/
  config.py               Settings (pydantic-settings)
  models.py               PromptData, ModelResponse
  engage.py               Engage levels and password check
  state.py                Typed session state + cached service accessors
  services/ai_service.py  AIService interface, GeminiService (google-genai, streaming)
  agent/                  ADK agent: agent.py (runner wrapper), tools.py, prompt.py
  ui/                     components.py (shared widgets), style.css
  views/                  One module per page: playground, engage, reservation, documentation
tests/                    pytest suite (no network needed)
```

Views own their UI and call services; services never import Streamlit, so they can
be tested and reused on their own.

## Development

```bash
pip install -r requirements-dev.txt
pytest
ruff check . && ruff format .
```

## Note on the Reservation agent

`read_from_disc` is deliberately over-permissive and serves a **fake** secret for
`.env` files: the agent is a sandbox for practising prompt injection and
excessive-agency attacks. Never connect it to real files or credentials.
