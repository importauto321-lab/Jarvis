"""The checker: a second opinion on a big decision. It only READS text you give it and answers.
Default checker is Gemini (free plan, GEMINI_API_KEY). ChatGPT can be added later (OPENAI_API_KEY, paid).
OFF until you add --live and have a key. NOT tested against real Gemini or ChatGPT: reply formats are unverified."""
import json
import os
import urllib.error
import urllib.request

URL = "https://api.openai.com/v1/chat/completions"
INSTRUCTIONS = ("You are a careful second reviewer for a small car hauling business. Read the text and reply in "
                "this form: VERDICT: agree or disagree. WHY: two or three short sentences. RISKS: anything "
                "missing or wrong. If it involves money, legal matters, or a demand letter, say a human "
                "professional must review it. Do not invent facts.")


def _http_help(code: int) -> str:
    return {401: "OpenAI says the key is wrong. Check OPENAI_API_KEY (no spaces, whole key).",
            429: "OpenAI says no credit left or too many requests. Check billing at platform.openai.com.",
            404: "OpenAI does not know that model name. Check 'openai_model' in settings.json."
            }.get(code, f"OpenAI returned error {code}. Nothing was changed.")


def second_opinion(text: str, model: str = "gpt-4o-mini", key: str = "", post=None) -> str:
    key = key or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise SystemExit("No OpenAI key yet. Set OPENAI_API_KEY at home first (never paste it in chat).")
    body = json.dumps({"model": model, "messages": [{"role": "system", "content": INSTRUCTIONS},
                                                    {"role": "user", "content": text}]}).encode()
    req = urllib.request.Request(URL, body, {"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    try:
        with (post or urllib.request.urlopen)(req, timeout=60) as r:
            return json.load(r)["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        raise SystemExit(_http_help(e.code))
    except urllib.error.URLError as e:
        raise SystemExit(f"Could not reach OpenAI ({e.reason}). Check the internet and try again.")
    except (KeyError, IndexError, ValueError):
        raise SystemExit("OpenAI replied in a form I did not expect. Nothing was changed; try again.")


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"


def second_opinion_gemini(text: str, key: str = "", post=None) -> str:
    key = key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise SystemExit("No Gemini key yet. Get a free one at aistudio.google.com and set GEMINI_API_KEY at home.")
    body = json.dumps({"contents": [{"parts": [{"text": INSTRUCTIONS + "\n\nTEXT TO REVIEW:\n" + text}]}]}).encode()
    req = urllib.request.Request(GEMINI_URL, body, {"Content-Type": "application/json", "x-goog-api-key": key})
    with (post or urllib.request.urlopen)(req, timeout=60) as r:
        data = json.load(r)
    return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
