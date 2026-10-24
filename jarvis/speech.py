"""Input (listening) and output (speaking) backends.

Voice backends import their heavy dependencies lazily so the assistant still
runs in text mode on machines without a microphone or audio drivers.
"""

from __future__ import annotations

from typing import Optional, Protocol


class Listener(Protocol):
    def listen(self) -> Optional[str]:
        """Return the next utterance, "" if nothing was understood, or None to quit."""


class Speaker(Protocol):
    def say(self, text: str) -> None: ...


class TextListener:
    """Reads commands from the keyboard."""

    def __init__(self, prompt: str = "You: ") -> None:
        self.prompt = prompt

    def listen(self) -> Optional[str]:
        try:
            return input(self.prompt)
        except (EOFError, KeyboardInterrupt):
            return None


class MicrophoneListener:
    """Captures speech from the default microphone and transcribes it."""

    def __init__(self, energy_threshold: int = 300, phrase_time_limit: float = 8.0) -> None:
        import speech_recognition as sr

        self._sr = sr
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.dynamic_energy_threshold = True
        self.microphone = sr.Microphone()
        self.phrase_time_limit = phrase_time_limit
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

    def listen(self) -> Optional[str]:
        sr = self._sr
        try:
            with self.microphone as source:
                print("Listening...")
                audio = self.recognizer.listen(source, phrase_time_limit=self.phrase_time_limit)
            text = self.recognizer.recognize_google(audio)
            print(f"You: {text}")
            return text
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as exc:
            print(f"[speech recognition unavailable: {exc}]")
            return ""
        except KeyboardInterrupt:
            return None


class ConsoleSpeaker:
    """Prints responses instead of speaking them."""

    def __init__(self, name: str = "Jarvis") -> None:
        self.name = name

    def say(self, text: str) -> None:
        print(f"{self.name}: {text}")


class VoiceSpeaker:
    """Speaks responses aloud with the offline pyttsx3 engine, and echoes them to the console."""

    def __init__(self, name: str = "Jarvis", rate: int = 180) -> None:
        import pyttsx3

        self.name = name
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", rate)

    def say(self, text: str) -> None:
        print(f"{self.name}: {text}")
        self.engine.say(text)
        self.engine.runAndWait()
