"""Open-ended conversation backed by Claude, used when no local skill matches."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

SYSTEM_PROMPT = """You are {name}, a friendly voice assistant. Your replies are read aloud by a \
text-to-speech engine, so answer in one to three short, natural spoken sentences. Never use \
markdown, bullet points, code blocks, emoji, or URLs. Spell out symbols when it helps them \
sound right. If a question needs a long answer, give the key point and offer to go deeper."""


class Brain:
    def __init__(self, name: str, model: str, effort: str = "low") -> None:
        import anthropic

        self._anthropic = anthropic
        self.client = anthropic.Anthropic()
        self.model = model
        self.effort = effort
        self.system = SYSTEM_PROMPT.format(name=name)
        self.messages: List[dict] = []

    def ask(self, question: str) -> str:
        anthropic = self._anthropic
        self.messages.append({"role": "user", "content": question})
        try:
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=16000,
                system=self.system,
                messages=self.messages,
                output_config={"effort": self.effort},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.AuthenticationError:
            self.messages.pop()
            return "I can't reach my language model. Please check the Anthropic API key."
        except anthropic.RateLimitError:
            self.messages.pop()
            return "I'm being rate limited right now. Try again in a moment."
        except anthropic.APIStatusError as exc:
            self.messages.pop()
            return f"My language model returned an error, status {exc.status_code}."
        except anthropic.APIConnectionError:
            self.messages.pop()
            return "I can't connect to the internet right now."

        if response.stop_reason == "refusal":
            self.messages.pop()
            return "Sorry, I can't help with that one."

        # Keep the full content (including thinking blocks) so history stays append-only.
        self.messages.append({"role": "assistant", "content": response.content})
        text = " ".join(b.text for b in response.content if b.type == "text").strip()
        return text or "I'm not sure what to say to that."

    def reset(self) -> None:
        self.messages.clear()


def make_brain(name: str, model: str, effort: str):
    """Return a Brain, or None if the SDK isn't installed or no credentials are configured."""
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return None
    has_credentials = any(
        os.environ.get(var) for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE")
    ) or (Path.home() / ".config" / "anthropic").exists()
    if not has_credentials:
        return None
    try:
        return Brain(name, model, effort)
    except Exception:
        return None
