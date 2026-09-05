"""Configuration for the LLM Council."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Council members - list of OpenRouter model identifiers
COUNCIL_MODELS = [
    "openai/gpt-5.1",
    "google/gemini-3-pro-preview",
    "anthropic/claude-sonnet-4.5",
    "x-ai/grok-4",
]

# Chairman model - synthesizes final response
CHAIRMAN_MODEL = "google/gemini-3-pro-preview"

# Cheap/fast model used for conversation titles
TITLE_MODEL = "google/gemini-2.5-flash"

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Home directory for all council state. Absolute, so the CLI and the MCP
# server write to the same store no matter which repo they are invoked from.
COUNCIL_HOME = Path(
    os.getenv("LLM_COUNCIL_HOME", Path.home() / ".llm-council")
).expanduser()

# Data directory for conversation storage
DATA_DIR = str(COUNCIL_HOME / "conversations")


class MissingAPIKeyError(RuntimeError):
    """Raised when OPENROUTER_API_KEY is not configured."""


def require_api_key() -> str:
    """Return the API key or fail with an actionable message."""
    if not OPENROUTER_API_KEY:
        raise MissingAPIKeyError(
            "OPENROUTER_API_KEY is not set. Put it in "
            f"{Path(__file__).resolve().parent.parent / '.env'} as "
            "OPENROUTER_API_KEY=sk-or-v1-... or export it in your shell."
        )
    return OPENROUTER_API_KEY
