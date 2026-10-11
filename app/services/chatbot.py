"""Food-spot chatbot: find matching analysed Reels, let the model pick and explain them.

The model only chooses which spots fit and why; the details and the Reel links
are rendered from the database, so a link can never be invented.
"""

import json
import logging
import os
import re

import httpx

from app.models import reels as reel_store
from app.services.openai_api import API_BASE, auth_headers, check
from app.services.reel_analysis import response_text

log = logging.getLogger("graphghost.chat")

MAX_CANDIDATES = 20    # spots sent to the model when the question has matching words
FALLBACK_SPOTS = 30    # spots sent when no word matches (e.g. "something spicy")
MAX_ANSWER_SPOTS = 5
HISTORY_TURNS = 6

STOPWORDS = {
    "the", "and", "for", "with", "any", "can", "you", "show", "give", "tell", "about",
    "near", "best", "good", "great", "some", "where", "what", "which", "place", "places",
    "spot", "spots", "food", "eat", "restaurant", "restaurants", "have", "has", "are",
    "that", "this", "from", "please", "need", "want", "find", "suggest", "recommend",
}

PROMPT = (
    "You are a food discovery assistant. Answer using ONLY the spots listed below, which "
    "come from Instagram Reels. Never invent a restaurant, address or detail. Return valid "
    "JSON only, without Markdown, with exactly these keys: answer (one or two friendly "
    "sentences, in the same language as the user's question) and spots (an array of at most "
    f"{MAX_ANSWER_SPOTS} objects, best match first, each with code, copied exactly from the "
    "list, and reason, one short sentence saying why it fits the question). If nothing in the "
    "list fits, return an empty spots array and say so in answer. Mention uncertainty in the "
    "reason when a spot has needs_verification true or a low confidence."
)


def reel_url(code: str) -> str:
    return f"https://www.instagram.com/reel/{code}/"


def to_spot(reel: dict) -> dict:
    """A compact, model- and display-friendly view of one analysed Reel."""
    analysis = reel["analysis"]
    places = [
        {key: place.get(key) for key in ("location_name", "full_address", "locality", "district", "state")}
        for place in analysis["addresses"]
    ]
    return {
        "code": reel["code"],
        "url": reel_url(reel["code"]),
        "restaurant_name": analysis["restaurant_name"],
        "food_items": analysis["food_items"],
        "places": places,
        "price_information": analysis["price_information"],
        "summary": analysis["reel_summary"],
        "highlights": analysis["highlights"][:3],
        "confidence": analysis["confidence"],
        "needs_verification": analysis["needs_verification"],
        "author": reel["author"],
    }


def search_terms(message: str) -> list[str]:
    words = re.findall(r"[\w']+", message.lower())
    return [word for word in words if len(word) >= 3 and word not in STOPWORDS]


def find_candidates(message: str) -> list[dict]:
    """Spots whose text contains words from the question, best matches first."""
    reels = [reel for reel in reel_store.list_reels() if reel["analysis"]]
    spots = [(to_spot(reel), (reel["caption"] or "")) for reel in reels]
    terms = search_terms(message)

    scored = []
    for spot, caption in spots:
        text = (json.dumps(spot, ensure_ascii=False) + " " + caption).lower()
        score = sum(term in text for term in terms)
        if score:
            scored.append((score, spot))
    if scored:
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [spot for _, spot in scored[:MAX_CANDIDATES]]
    return [spot for spot, _ in spots][-FALLBACK_SPOTS:]


def parse_model_json(text: str) -> dict:
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"The model did not return valid JSON: {error}") from error
    if not isinstance(data, dict) or "answer" not in data or "spots" not in data:
        raise RuntimeError("The model's reply is missing required keys.")
    return data


def ask_model(message: str, history: list[dict], spots: list[dict]) -> dict:
    model = os.environ.get(
        "OPENAI_CHAT_MODEL", os.environ.get("OPENAI_ANALYSIS_MODEL", "gpt-6-luna")
    )
    conversation = "\n".join(
        f"{turn['role']}: {turn['content']}" for turn in history[-HISTORY_TURNS:]
    )
    content = (
        f"{PROMPT}\n\nSpots:\n{json.dumps(spots, ensure_ascii=False, separators=(',', ':'))}"
        f"\n\nConversation so far:\n{conversation or '(none)'}\n\nUser question: {message}"
    )
    log.info("Chat: %d candidate spot(s) sent to %s", len(spots), model)
    response = httpx.post(
        f"{API_BASE}/responses",
        headers=auth_headers(),
        json={"model": model, "input": [{"role": "user", "content": content}]},
        timeout=120,
    )
    return parse_model_json(response_text(check(response)))


def place_line(spot: dict) -> str:
    """One readable location, e.g. "Kakkanad, Ernakulam"."""
    for place in spot["places"]:
        parts = [place.get("locality") or place.get("location_name"), place.get("district")]
        line = ", ".join(dict.fromkeys(part for part in parts if part))
        if line:
            return line
    return ""


def format_reply(answer: str, spots: list[dict]) -> str:
    """Plain Markdown version of the answer for clients that show text."""
    lines = [answer]
    for number, spot in enumerate(spots, start=1):
        title = spot["restaurant_name"] or "Unnamed spot"
        where = place_line(spot)
        lines += ["", f"**{number}. {title}**" + (f" - {where}" if where else "")]
        if spot["food_items"]:
            lines.append(f"- Food: {', '.join(spot['food_items'])}")
        if spot["price_information"]:
            lines.append(f"- Price: {spot['price_information']}")
        lines.append(f"- Why: {spot['reason']}")
        if spot["needs_verification"]:
            lines.append("- Note: details need verification")
        lines.append(f"- Reel: {spot['url']}")
    return "\n".join(lines)


def answer_question(message: str, history: list[dict]) -> dict:
    """Return {"answer", "spots", "reply"} for a food-spot question."""
    candidates = find_candidates(message)
    if not candidates:
        text = "I don't have any analysed Reels yet. Collect and transcribe some first."
        return {"answer": text, "spots": [], "reply": text}

    data = ask_model(message, history, candidates)
    by_code = {spot["code"]: spot for spot in candidates}

    chosen = []
    for item in data["spots"] if isinstance(data["spots"], list) else []:
        code = item.get("code") if isinstance(item, dict) else None
        if code in by_code:  # ignore anything the model made up
            chosen.append({**by_code[code], "reason": str(item.get("reason") or "")})
    chosen = chosen[:MAX_ANSWER_SPOTS]

    answer = str(data["answer"])
    return {"answer": answer, "spots": chosen, "reply": format_reply(answer, chosen)}
