import os
from pathlib import Path

import httpx

from app.services.openai_api import API_BASE, auth_headers, check

# Hint that helps the model with Malayalam, Manglish and local names.
TRANSCRIPTION_PROMPT = (
    "The audio may contain Malayalam, Manglish, Kerala place names, "
    "food names, and restaurant names."
)


def transcribe(video_path: Path) -> str:
    """Send the video's audio to OpenAI and return the transcript text."""
    model = os.environ.get("OPENAI_TRANSCRIBE_MODEL", "gpt-transcribe")
    with video_path.open("rb") as video:
        response = httpx.post(
            f"{API_BASE}/audio/transcriptions",
            headers=auth_headers(),
            data={"model": model, "prompt": TRANSCRIPTION_PROMPT},
            files={"file": (video_path.name, video, "video/mp4")},
            timeout=300,
        )
    return check(response)["text"]
