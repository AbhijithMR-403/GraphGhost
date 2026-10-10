import json
import os
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

from app.scraper.browser import launch_context

# Instagram embeds page data as JSON inside script tags of the HTML document.
SCRIPT_JSON_PATTERN = re.compile(
    r'<script type="application/json"[^>]*>(.*?)</script>', re.DOTALL
)
REEL_CODE_PATTERN = re.compile(r"instagram\.com/(?:reel|reels)/([A-Za-z0-9_-]+)")


def video_url_of(media: dict) -> str | None:
    versions = media.get("video_versions")
    if isinstance(versions, list) and versions and versions[0].get("url"):
        return versions[0]["url"]
    return media.get("video_url")


def find_media(data, code: str) -> dict | None:
    """Walk parsed JSON and return the media object for this Reel code.

    A Reel page also loads suggested Reels, so the shortcode must be checked;
    taking the first video found downloads the wrong Reel.
    """
    if isinstance(data, dict):
        if code in (data.get("code"), data.get("shortcode")) and video_url_of(data):
            return data
        children = data.values()
    elif isinstance(data, list):
        children = data
    else:
        return None

    for child in children:
        media = find_media(child, code)
        if media:
            return media
    return None


def details_of(media: dict) -> dict:
    """Pick the human-useful fields out of Instagram's media object."""
    caption = media.get("caption") or {}
    user = media.get("user") or media.get("owner") or {}
    return {
        "caption": caption.get("text") if isinstance(caption, dict) else None,
        "author": user.get("username"),
        "author_name": user.get("full_name"),
        "posted_at": media.get("taken_at"),  # Unix seconds
        "likes": media.get("like_count"),
        "comments": media.get("comment_count"),
    }


def get_media(page, reel_url: str, code: str) -> dict | None:
    """Open the Reel and read its media object from the JSON responses the page loads.

    Unauthenticated GraphQL calls are rejected by Instagram (HTTP 403), so this
    relies on the saved logged-in profile instead of a hard-coded doc_id.
    """
    found: list[dict] = []

    def on_response(response) -> None:
        # Data arrives embedded in the HTML document or as XHR/fetch responses,
        # some labelled text/javascript, so the content type is not trusted.
        if not response.url.startswith("https://www.instagram.com/"):
            return
        kind = response.request.resource_type
        if kind not in ("document", "xhr", "fetch"):
            return
        try:
            text = response.text()
            if kind == "document":
                blobs = [json.loads(blob) for blob in SCRIPT_JSON_PATTERN.findall(text)]
            else:
                blobs = [json.loads(text)]
        except Exception:
            return  # body unavailable or not JSON; ignore this response
        for blob in blobs:
            media = find_media(blob, code)
            if media:
                found.append(media)
                return

    page.on("response", on_response)
    try:
        page.goto(reel_url, wait_until="domcontentloaded")
        for _ in range(20):  # wait up to ~10 s for the data request
            if found:
                break
            page.wait_for_timeout(500)
    finally:
        page.remove_listener("response", on_response)

    return found[0] if found else None


def download_reel(context, page, reel_url: str, output_dir: Path) -> dict:
    """Download one Reel; return {"url", "ok", "message", "path", "details"}.

    path is relative to the current directory (the project root), e.g. downloads/<code>.mp4.
    """
    result = {"url": reel_url, "ok": False, "message": "", "path": None, "details": None}

    match = REEL_CODE_PATTERN.search(reel_url)
    if not match:
        result["message"] = "Not a Reel URL."
        return result

    target = output_dir / f"{match.group(1)}.mp4"
    result["path"] = Path(os.path.relpath(target)).as_posix()
    if target.exists():
        result.update(ok=True, message="Already downloaded.")
        return result

    media = get_media(page, reel_url, match.group(1))
    if not media:
        result["message"] = "No video found for this Reel (logged out, or Instagram changed its data?)."
        return result

    result["details"] = details_of(media)
    response = context.request.get(video_url_of(media))
    if not response.ok:
        result["message"] = f"Download failed with HTTP {response.status}."
        return result

    target.write_bytes(response.body())
    result.update(ok=True, message="Saved.")
    return result


def download_reels(
    urls: list[str], output_dir: Path, headless: bool = True, on_result=None
) -> list[dict]:
    """Download every URL with the saved login profile; one result per URL."""
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []

    with sync_playwright() as p:
        context = launch_context(p, headless=headless)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            for reel_url in urls:
                try:
                    result = download_reel(context, page, reel_url, output_dir)
                except Exception as error:
                    result = {"url": reel_url, "ok": False, "message": str(error), "path": None, "details": None}
                results.append(result)
                print(f'{"OK  " if result["ok"] else "FAIL"} {reel_url} {result["message"]}')
                if on_result:
                    on_result(result, results)
        finally:
            context.close()

    return results
