"""Shared fixtures: an isolated store and a stubbed model client.

The council's only external dependency is OpenRouter. Every test here replaces
that one call, so the whole suite runs offline, deterministically and for free.
"""

import asyncio
import random
import re

import pytest

from backend import council, openrouter, storage


def fake_response(content: str) -> dict:
    """Shape a stub reply exactly like openrouter.query_model returns."""
    return {
        "content": content,
        "reasoning_details": None,
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "cost": 0.001},
        "duration": 0.1,
    }


def build_fake_client(failing_models=(), chairman_fails=False):
    """A stand-in for query_model that answers by prompt type.

    Args:
        failing_models: models that return None, to exercise graceful degradation
        chairman_fails: make the synthesis step fail
    """

    async def fake_query_model(model, messages, timeout=120.0, max_retries=2):
        prompt = messages[0]["content"]
        await asyncio.sleep(0)

        if "You are the Chairman" in prompt:
            if chairman_fails:
                return None
            return fake_response(
                "## Empfehlung\nNimm A.\n\n## Dissens im Konzil\nKeiner.\n\n"
                f"(kontext={'# Kontext' in prompt}, "
                f"schema={'## Empfehlung' in prompt or '## Kurzfassung' in prompt})"
            )

        if model in failing_models:
            return None

        if "Generate a very short title" in prompt:
            return fake_response("Ein kurzer Titel")

        if "FINAL RANKING:" in prompt:
            labels = sorted({m[:-1] for m in re.findall(r"Response [A-Z]:", prompt)})
            random.Random(model).shuffle(labels)
            ranked = "\n".join(f"{i}. {l}" for i, l in enumerate(labels, 1))
            return fake_response(
                f"Bewertung von {model}.\n\nFINAL RANKING:\n{ranked}"
            )

        return fake_response(f"Stage-1-Antwort von {model}.")

    return fake_query_model


@pytest.fixture
def stub_models(monkeypatch):
    """Replace the model client. Yields a setter for special-case clients."""

    def install(**kwargs):
        client = build_fake_client(**kwargs)
        monkeypatch.setattr(openrouter, "query_model", client)
        monkeypatch.setattr(council, "query_model", client)
        return client

    install()
    return install


@pytest.fixture
def store(tmp_path, monkeypatch):
    """Point conversation storage at a throwaway directory.

    storage.py binds DATA_DIR at import time, so patching the module attribute
    is what actually redirects writes.
    """
    data_dir = tmp_path / "conversations"
    monkeypatch.setattr(storage, "DATA_DIR", str(data_dir))
    return data_dir
