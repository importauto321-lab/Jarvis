"""The main listen -> understand -> respond loop."""

from __future__ import annotations

import re
from typing import Optional

from .config import Config
from .skills import Context, Exit, run_skills
from .speech import Listener, Speaker


class Assistant:
    def __init__(self, config: Config, listener: Listener, speaker: Speaker, brain=None, context: Optional[Context] = None) -> None:
        self.config = config
        self.listener = listener
        self.speaker = speaker
        self.brain = brain
        self.context = context or Context(config=config, speaker=speaker)
        self._wake = re.compile(rf"^\W*(?:hey |ok |okay )?{re.escape(config.wake_word)}\b[\s,.!?]*", re.IGNORECASE)

    def strip_wake_word(self, utterance: str) -> Optional[str]:
        """Return the command after the wake word, "" if only the wake word was said, or None if absent."""
        match = self._wake.search(utterance)
        if match:
            return utterance[match.end():].strip()
        return None if self.config.require_wake_word else utterance.strip()

    def respond(self, command: str) -> str:
        """Produce a reply for a command. Raises ``Exit`` when the user says goodbye."""
        command = command.strip().rstrip(".!")
        reply = run_skills(self.context, command)
        if reply is not None:
            return reply
        if self.brain is not None:
            return self.brain.ask(command)
        return ("I don't know how to do that yet. Set an Anthropic API key to let me answer "
                "general questions, or say 'search for' followed by your question.")

    def run(self) -> None:
        cfg = self.config
        hint = f" Say '{cfg.wake_word}' followed by a command." if cfg.require_wake_word else ""
        self.speaker.say(f"{cfg.name} online.{hint}")
        awaiting_command = False
        while True:
            utterance = self.listener.listen()
            if utterance is None:
                self.speaker.say("Goodbye.")
                break
            if not utterance.strip():
                continue

            command = utterance.strip() if awaiting_command else self.strip_wake_word(utterance)
            awaiting_command = False
            if command is None:
                continue
            if command == "":
                self.speaker.say("Yes?")
                awaiting_command = True
                continue

            try:
                self.speaker.say(self.respond(command))
            except Exit as farewell:
                self.speaker.say(farewell.farewell)
                break
        for timer in self.context.timers:
            timer.cancel()
