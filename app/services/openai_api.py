import os

import httpx
from dotenv import load_dotenv

load_dotenv()  # OPENAI_API_KEY and model names come from .env (see .env.example)

API_BASE = "https://api.openai.com/v1"


def auth_headers() -> dict[str, str]:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env.")
    return {"Authorization": f"Bearer {key}"}


def check(response: httpx.Response) -> dict:
    """Return the JSON body, or raise with OpenAI's own error message."""
    if response.status_code >= 400:
        try:
            detail = response.json()["error"]["message"]
        except Exception:
            detail = response.text[:300]
        raise RuntimeError(f"OpenAI returned HTTP {response.status_code}: {detail}")
    return response.json()
