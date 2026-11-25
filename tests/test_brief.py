import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import brief  # noqa: E402


@pytest.mark.parametrize("worker", ["gemini", "chatgpt", "hermes"])
def test_the_generated_message_is_complete(worker):
    assert brief.missing(worker, brief.message(worker)) == []


def test_a_left_out_line_is_caught(tmp_path, capsys):
    short = brief.message("gemini").replace("Listening to audio and transcribing it.", "")
    assert brief.missing("gemini", short) == ["Listening to audio and transcribing it."]
    note = tmp_path / "n.txt"
    note.write_text(short)
    assert brief.main(["gemini", "--check", str(note)]) == 1
    assert "NOT COMPLETE" in capsys.readouterr().out
    note.write_text(brief.message("gemini"))
    assert brief.main(["gemini", "--check", str(note)]) == 0


def test_unknown_worker_and_bad_usage(capsys):
    assert brief.main(["siri"]) == 2
    assert "No saved list" in capsys.readouterr().out
    assert brief.main([]) == 2
