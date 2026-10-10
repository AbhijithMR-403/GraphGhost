import json
import os

import httpx

from app.services.openai_api import API_BASE, auth_headers, check

EXPECTED_KEYS = {
    "reel_summary", "language", "food_items", "restaurant_name", "addresses",
    "price_information", "highlights", "sentiment", "confidence", "needs_verification",
}

PROMPT = (
    "Analyze this Instagram Reel transcript for a food discovery application. "
    "Extract only details supported by the transcript. Do not invent restaurant names, "
    "addresses, or locations. If a detail is unknown, use null or an empty array as "
    "appropriate. Return valid JSON only, with exactly these keys: reel_summary, language, "
    "food_items, restaurant_name, addresses, price_information, highlights, sentiment, "
    "confidence, needs_verification. Field requirements: reel_summary is a concise summary; "
    "language is the spoken language; food_items is an array of food or drink names; "
    "restaurant_name is the mentioned restaurant name, or null if unknown; addresses is an "
    "array of candidate locations or addresses, including conflicting possibilities. Each "
    "addresses item must contain these keys: location_name, full_address, locality, district, "
    "state, country, evidence, confidence, and source. Use null for unknown values. evidence "
    "must quote the relevant transcript text. confidence must be a number from 0 to 1. source "
    "must be transcript, visual, or both. Keep separate candidates separate; do not combine "
    "conflicting places into one address. price_information contains mentioned prices or "
    "offers, or null; highlights is an array of notable details; sentiment is the overall "
    "tone, or null; confidence is an overall extraction confidence from 0 to 1; "
    "needs_verification is true if important details are ambiguous or uncertain. Return JSON "
    "only, without Markdown. Transcript: "
)


def response_text(body: dict) -> str:
    """Join the output_text parts of a Responses API reply."""
    parts = [
        part["text"]
        for item in body.get("output", [])
        if item.get("type") == "message"
        for part in item.get("content", [])
        if part.get("type") == "output_text"
    ]
    return "".join(parts).strip()


def analyze(transcript: str) -> dict:
    """Ask the model to extract food-discovery details from a transcript."""
    model = os.environ.get("OPENAI_ANALYSIS_MODEL", "gpt-6-luna")
    response = httpx.post(
        f"{API_BASE}/responses",
        headers=auth_headers(),
        json={"model": model, "input": [{"role": "user", "content": PROMPT + transcript}]},
        timeout=120,
    )
    text = response_text(check(response))

    # The prompt forbids Markdown, but tolerate a fenced reply.
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        analysis = json.loads(text)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"The model did not return valid JSON: {error}") from error

    if not isinstance(analysis, dict) or not EXPECTED_KEYS <= analysis.keys():
        raise RuntimeError("The model's JSON is missing required keys.")
    return analysis
