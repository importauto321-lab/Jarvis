"""Command-line entry point: ``python -m jarvis``."""

from __future__ import annotations

import argparse
import sys

from .assistant import Assistant
from .brain import make_brain
from .config import Config
from .speech import ConsoleSpeaker, MicrophoneListener, TextListener, VoiceSpeaker


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="jarvis", description="A simple voice assistant.")
    parser.add_argument("--text", action="store_true", help="type commands instead of speaking them")
    parser.add_argument("--mute", action="store_true", help="print replies instead of speaking them")
    parser.add_argument("--wake-word", help="word that activates the assistant (default: jarvis)")
    parser.add_argument("--name", help="what the assistant calls itself")
    parser.add_argument("--no-wake-word", action="store_true", help="respond to everything, no wake word needed")
    parser.add_argument("--no-ai", action="store_true", help="use only built-in skills, never call Claude")
    args = parser.parse_args(argv)

    config = Config()
    if args.wake_word:
        config.wake_word = args.wake_word
        if not args.name:
            config.name = args.wake_word.title()
    if args.name:
        config.name = args.name
    if args.no_wake_word or args.text:
        config.require_wake_word = False

    if args.text:
        listener = TextListener()
    else:
        try:
            listener = MicrophoneListener()
        except Exception as exc:  # missing PyAudio / no microphone
            print(f"Microphone unavailable ({exc}); falling back to text mode.", file=sys.stderr)
            listener = TextListener()
            config.require_wake_word = False

    speaker = ConsoleSpeaker(config.name)
    if not args.mute:
        try:
            speaker = VoiceSpeaker(config.name, config.voice_rate)
        except Exception as exc:  # missing pyttsx3 / no speech engine
            print(f"Text-to-speech unavailable ({exc}); printing replies instead.", file=sys.stderr)

    brain = None if args.no_ai else make_brain(config.name, config.model, config.effort,
                                              config.gemini_api_key, config.gemini_model)
    if brain is None and not args.no_ai:
        print("No Anthropic credentials found; general questions are disabled.", file=sys.stderr)

    Assistant(config, listener, speaker, brain).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
