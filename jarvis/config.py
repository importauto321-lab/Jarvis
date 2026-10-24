"""Runtime configuration, read from environment variables with sane defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Config:
    name: str = field(default_factory=lambda: os.environ.get("JARVIS_NAME", "Jarvis"))
    wake_word: str = field(default_factory=lambda: os.environ.get("JARVIS_WAKE_WORD", "jarvis"))
    require_wake_word: bool = field(default_factory=lambda: _env_bool("JARVIS_REQUIRE_WAKE_WORD", True))
    model: str = field(default_factory=lambda: os.environ.get("JARVIS_MODEL", "claude-opus-5-5"))
    effort: str = field(default_factory=lambda: os.environ.get("JARVIS_EFFORT", "low"))
    voice_rate: int = field(default_factory=lambda: int(os.environ.get("JARVIS_VOICE_RATE", "180")))
    notes_file: Path = field(
        default_factory=lambda: Path(os.environ.get("JARVIS_NOTES_FILE", Path.home() / ".jarvis_notes.txt"))
    )
