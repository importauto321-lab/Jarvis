"""ChatGPT as the checker: a second opinion on a big decision. It only READS text you give it and answers.
OFF until there is an OpenAI key (OPENAI_API_KEY in the environment at home) and you add --live.
NOT tested against real ChatGPT: the model name and reply format are unverified."""
import json
import os
import urllib.request

URL = "https://api.openai.com/v1/chat/completions"
INSTRUCTIONS = ("You are a careful second reviewer for a small car hauling business. Read the text and reply in "
                "this form: VERDICT: agree or disagree. WHY: two or three short sentences. RISKS: anything "
                "missing or wrong. If it involves money, legal matters, or a demand letter, say a human "
                "professional must review it. Do not invent facts.")


def second_opinion(text: str, model: str = "gpt-4o-mini", key: str = "", post=None) -> str:
    key = key or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise SystemExit("No OpenAI key yet. Set OPENAI_API_KEY at home first (never paste it in chat).")
    body = json.dumps({"model": model, "messages": [{"role": "system", "content": INSTRUCTIONS},
                                                    {"role": "user", "content": text}]}).encode()
    req = urllib.request.Request(URL, body, {"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    with (post or urllib.request.urlopen)(req, timeout=60) as r:
        return json.load(r)["choices"][0]["message"]["content"]
