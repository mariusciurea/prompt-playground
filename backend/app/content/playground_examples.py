"""Ready-made Playground prompts."""

from pydantic import BaseModel, ConfigDict


class PlaygroundExample(BaseModel):
    """A system + user prompt pair to start from."""

    model_config = ConfigDict(frozen=True)

    id: str
    label: str
    system_prompt: str
    user_prompt: str


PLAYGROUND_EXAMPLES: tuple[PlaygroundExample, ...] = (
    PlaygroundExample(
        id="translator",
        label="Translator",
        system_prompt=(
            "You are a professional translator. Translate the user's text into French, "
            "preserving tone and register. Reply with the translation only."
        ),
        user_prompt="The quick brown fox jumps over the lazy dog.",
    ),
    PlaygroundExample(
        id="pirate",
        label="Pirate",
        system_prompt=(
            "You are a pirate captain. Answer everything in pirate speak, "
            "with plenty of nautical metaphors."
        ),
        user_prompt="How do I make a good cup of coffee?",
    ),
    PlaygroundExample(
        id="code-reviewer",
        label="Code reviewer",
        system_prompt=(
            "You are a senior Python reviewer. Point out bugs first, then style issues. Be concise."
        ),
        user_prompt="def add(a, b):\n    return a - b\n\nprint(add(2, 3))",
    ),
    PlaygroundExample(
        id="summarizer",
        label="Summarizer",
        system_prompt="Summarize the user's text in exactly three bullet points.",
        user_prompt=(
            "Large language models are trained on vast text corpora to predict the next token. "
            "Prompt engineering is the practice of crafting inputs that steer the model toward "
            "useful, accurate and safe outputs, using techniques like few-shot examples, "
            "role prompting and chain-of-thought reasoning."
        ),
    ),
    PlaygroundExample(
        id="json-extractor",
        label="JSON extractor",
        system_prompt=(
            "Extract entities from the text and answer with valid JSON only, using the keys "
            '"people", "places" and "dates".'
        ),
        user_prompt="Ada Lovelace met Charles Babbage in London on 5 June 1833.",
    ),
)
