"""Built-in skills that run locally, without calling a language model.

A skill is a regular expression plus a handler. The first skill whose pattern
matches the (wake-word-stripped) command handles it. Add your own with the
``@skill`` decorator.
"""

from __future__ import annotations

import ast
import datetime as dt
import operator
import random
import re
import threading
import urllib.parse
import webbrowser
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .config import Config
from .speech import Speaker


class Exit(Exception):
    """Raised by a skill to end the session after saying goodbye."""

    def __init__(self, farewell: str) -> None:
        super().__init__(farewell)
        self.farewell = farewell


class NotMine(Exception):
    """Raised by a skill whose pattern matched but which can't handle the command."""


@dataclass
class Context:
    config: Config
    speaker: Speaker
    open_url: Callable[[str], object] = webbrowser.open
    now: Callable[[], dt.datetime] = dt.datetime.now
    timers: List[threading.Timer] = field(default_factory=list)


Handler = Callable[[Context, "re.Match[str]"], str]


@dataclass
class Skill:
    name: str
    pattern: "re.Pattern[str]"
    handler: Handler
    help: str


SKILLS: List[Skill] = []


def skill(name: str, pattern: str, help: str) -> Callable[[Handler], Handler]:
    def register(fn: Handler) -> Handler:
        SKILLS.append(Skill(name, re.compile(pattern, re.IGNORECASE), fn, help))
        return fn

    return register


def run_skills(ctx: Context, command: str) -> Optional[str]:
    """Return the reply of the first skill that handles ``command``, or None."""
    for s in SKILLS:
        match = s.pattern.search(command)
        if not match:
            continue
        try:
            return s.handler(ctx, match)
        except NotMine:
            continue
    return None


# --- conversation -----------------------------------------------------------

@skill("exit", r"^(good ?bye|bye|exit|quit|stop listening|shut ?down|go to sleep)\b", "say goodbye to end the session")
def _exit(ctx: Context, m: "re.Match[str]") -> str:
    raise Exit("Goodbye. Call me if you need anything.")


@skill("greeting", r"^(hi|hello|hey|good (morning|afternoon|evening))\b", "say hello")
def _greeting(ctx: Context, m: "re.Match[str]") -> str:
    hour = ctx.now().hour
    part = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"
    return f"Good {part}. How can I help?"


@skill("help", r"\b(what can you do|help|commands)\b", "ask what I can do")
def _help(ctx: Context, m: "re.Match[str]") -> str:
    items = [s.help for s in SKILLS if s.name not in {"help", "exit", "greeting"}]
    return f"I can {', '.join(items[:-1])}, and {items[-1]}. Anything else, just ask."


@skill("joke", r"\b(tell me a )?joke\b", "tell a joke")
def _joke(ctx: Context, m: "re.Match[str]") -> str:
    return random.choice(JOKES)


JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "I would tell you a UDP joke, but you might not get it.",
    "There are 10 kinds of people: those who understand binary and those who don't.",
    "Why did the computer go to the doctor? It had a virus.",
    "I told my computer I needed a break, and it said: no problem, I'll go to sleep.",
]


# --- time -------------------------------------------------------------------

@skill("time", r"\bwhat(?:'s| is) the time\b|\bwhat time is it\b|^time$", "tell the time")
def _time(ctx: Context, m: "re.Match[str]") -> str:
    now = ctx.now()
    return f"It's {now.strftime('%I:%M %p').lstrip('0')}."


@skill("date", r"\bwhat(?:'s| is) (?:the |today's )?date\b|\bwhat day is (it|today)\b", "tell the date")
def _date(ctx: Context, m: "re.Match[str]") -> str:
    now = ctx.now()
    return f"Today is {now.strftime('%A, %B')} {now.day}, {now.year}."


_UNITS = {"second": 1, "minute": 60, "hour": 3600}


@skill("timer", r"\b(?:set )?(?:a )?timer (?:for )?(\d+(?:\.\d+)?) (second|minute|hour)s?\b", "set a timer")
def _timer(ctx: Context, m: "re.Match[str]") -> str:
    amount, unit = float(m.group(1)), m.group(2).lower()
    seconds = amount * _UNITS[unit]
    label = f"{m.group(1)} {unit}{'' if amount == 1 else 's'}"
    timer = threading.Timer(seconds, ctx.speaker.say, args=(f"Your {label} timer is done.",))
    timer.daemon = True
    timer.start()
    ctx.timers.append(timer)
    return f"Timer set for {label}."


# --- maths ------------------------------------------------------------------

_WORD_OPS = [
    (r"\bmultiplied by\b|\btimes\b|\bx\b", "*"),
    (r"\bdivided by\b|\bover\b", "/"),
    (r"\bplus\b|\badded to\b", "+"),
    (r"\bminus\b|\bless\b", "-"),
    (r"\bto the power of\b|\bpower\b", "**"),
    (r"\bsquared\b", "**2"),
    (r"\bcubed\b", "**3"),
    (r"\bmod(ulo)?\b", "%"),
]

_BIN_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def safe_eval(expression: str) -> float:
    """Evaluate a plain arithmetic expression without using ``eval``."""

    def walk(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
            left, right = walk(node.left), walk(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise ValueError("exponent too large")
            return _BIN_OPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
            return _UNARY_OPS[type(node.op)](walk(node.operand))
        raise ValueError("unsupported expression")

    return walk(ast.parse(expression, mode="eval"))


def to_expression(text: str) -> Optional[str]:
    expr = text.lower().replace("?", "").replace(",", "")
    for pattern, symbol in _WORD_OPS:
        expr = re.sub(pattern, f" {symbol} ", expr)
    expr = expr.strip()
    if not re.fullmatch(r"[\d\s.+\-*/%()]+", expr) or not re.search(r"\d", expr):
        return None
    return expr


@skill("calculate", r"^(?:calculate|compute|what(?:'s| is))\s+(.+)$", "do arithmetic")
def _calculate(ctx: Context, m: "re.Match[str]") -> str:
    expr = to_expression(m.group(1))
    if expr is None:
        raise NotMine()
    try:
        result = safe_eval(expr)
    except (ValueError, SyntaxError, ZeroDivisionError):
        return "Sorry, I couldn't work that out."
    if isinstance(result, float) and result.is_integer():
        result = int(result)
    elif isinstance(result, float):
        result = round(result, 6)
    return f"That's {result}."


# --- web --------------------------------------------------------------------

SITES = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "wikipedia": "https://www.wikipedia.org",
    "maps": "https://maps.google.com",
    "news": "https://news.google.com",
}


@skill("open", r"^open (?:up )?(?:the )?([\w.\-]+)(?: website)?$", "open a website")
def _open(ctx: Context, m: "re.Match[str]") -> str:
    target = m.group(1).lower()
    url = SITES.get(target)
    if url is None:
        if "." not in target:
            target += ".com"
        url = f"https://{target}"
    ctx.open_url(url)
    return f"Opening {m.group(1)}."


@skill("search", r"^(?:search(?: the web| google)?(?: for)?|google|look up) (.+)$", "search the web")
def _search(ctx: Context, m: "re.Match[str]") -> str:
    query = m.group(1).strip()
    ctx.open_url("https://www.google.com/search?q=" + urllib.parse.quote_plus(query))
    return f"Here's what I found for {query}."


# --- notes ------------------------------------------------------------------

@skill("note", r"^(?:take a note|make a note|note|remember(?: that)?)[:,]?\s+(.+)$", "take notes")
def _note(ctx: Context, m: "re.Match[str]") -> str:
    path = ctx.config.notes_file
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"{ctx.now():%Y-%m-%d %H:%M} {m.group(1).strip()}\n")
    return "Got it, I've noted that."


@skill("read_notes", r"\b(read|what are) (back )?my notes\b", "read your notes back")
def _read_notes(ctx: Context, m: "re.Match[str]") -> str:
    path = ctx.config.notes_file
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return "You don't have any notes yet."
    lines = path.read_text(encoding="utf-8").strip().splitlines()[-5:]
    notes = ". ".join(line.split(" ", 2)[-1] for line in lines)
    return f"Your latest notes: {notes}."
