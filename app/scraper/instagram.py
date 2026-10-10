import re

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

INSTAGRAM_URL = "https://www.instagram.com/"
REEL_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?instagram\.com/(?:reel|reels)/([A-Za-z0-9_-]+)"
)


def open_group_conversation(page, group_name: str) -> None:
    """Open Messages from the Instagram home page, then select one group."""
    page.goto(INSTAGRAM_URL, wait_until="domcontentloaded")

    try:
        messages_link = page.locator('a[href^="/direct/"]').first
        messages_link.wait_for(state="visible", timeout=15_000)
        messages_link.click()
    except Exception as error:
        raise RuntimeError(
            "Could not find the Instagram Messages icon. Confirm the saved profile is logged in."
        ) from error

    try:
        page.get_by_text(group_name, exact=True).first.wait_for(
            state="visible", timeout=15_000
        )
        page.get_by_text(group_name, exact=True).first.click()
    except Exception as error:
        raise RuntimeError(
            f'Could not find the group named "{group_name}" in Messages.'
        ) from error

    page.wait_for_timeout(750)


# Reel messages in the chat show a "Clip" icon inside a clickable bubble.
REEL_BUBBLES = 'svg[aria-label="Clip"]'

# Runs in the page: find the chat's scrollable pane at the point (x, y), then
# report its scroll metrics and each rendered Reel bubble. A bubble's "key" is
# its offset inside the pane, which stays stable while scrolling, so the same
# Reel is recognised again on the next screen. Instagram only keeps nearby
# messages in the page, so the bubbles must be handled page by page.
CHAT_STATE_JS = """
([x, y, selector]) => {
    let pane = document.elementFromPoint(x, y);
    while (pane && !(pane.scrollHeight > pane.clientHeight + 20
            && /(auto|scroll)/.test(getComputedStyle(pane).overflowY))) {
        pane = pane.parentElement;
    }
    if (!pane) return null;
    const paneBox = pane.getBoundingClientRect();
    const reels = [...document.querySelectorAll(selector)].map(icon => {
        const box = icon.getBoundingClientRect();
        return {
            key: Math.round(pane.scrollTop + box.top - paneBox.top),
            visible: box.top >= paneBox.top && box.bottom <= paneBox.bottom,
        };
    });
    return {
        top: pane.scrollTop,
        height: pane.scrollHeight,
        client: pane.clientHeight,
        reels: reels,
    };
}
"""

KEY_TOLERANCE = 10  # pixels; absorbs sub-pixel layout jitter


def chat_point(page) -> tuple[int, int]:
    """A point over the chat pane (right side), not the inbox list on the left."""
    viewport = page.viewport_size
    return int(viewport["width"] * 0.75), viewport["height"] // 2


def chat_state(page) -> dict:
    x, y = chat_point(page)
    state = page.evaluate(CHAT_STATE_JS, [x, y, REEL_BUBBLES])
    if state is None:
        raise RuntimeError("Could not find the scrollable chat pane.")
    return state


def scroll_to_oldest_message(page, max_scrolls: int) -> None:
    """Scroll up until the pane is at the top and no older messages load."""
    page.mouse.move(*chat_point(page))
    previous_height = -1
    stable = 0
    for _ in range(max_scrolls):
        page.mouse.wheel(0, -3_000)
        page.wait_for_timeout(700)
        state = chat_state(page)
        at_top = state["top"] <= 1
        stable = stable + 1 if at_top and state["height"] == previous_height else 0
        previous_height = state["height"]
        if stable >= 3:
            return


def open_reel_and_get_url(page, index: int) -> str | None:
    """Click the index-th Reel bubble, read the /reel/<code>/ URL, and go back."""
    chat_url = page.url
    page.locator(REEL_BUBBLES).nth(index).click(timeout=5_000)

    try:
        page.wait_for_url(REEL_URL_PATTERN, timeout=8_000)
    except PlaywrightTimeoutError:
        print("URL did not change after clicking the Reel.")
        return None

    match = REEL_URL_PATTERN.search(page.url)
    reel_url = f"https://www.instagram.com/reel/{match.group(1)}/"

    page.go_back(wait_until="domcontentloaded", timeout=10_000)
    page.wait_for_url(chat_url, timeout=10_000)
    page.wait_for_timeout(1_000)  # Back keeps the scroll position; let bubbles render
    return reel_url


def next_unseen_reel(state: dict, seen_keys: list[int]) -> tuple[int, int] | None:
    """Return (index, key) of the first fully visible Reel not handled yet."""
    for index, reel in enumerate(state["reels"]):
        already_seen = any(abs(reel["key"] - key) <= KEY_TOLERANCE for key in seen_keys)
        if reel["visible"] and not already_seen:
            return index, reel["key"]
    return None


def collect_reel_urls(page, max_scrolls: int, on_url=None) -> list[str]:
    """Go from the oldest message down, opening every Reel on each screen.

    on_url(url, all_urls) is called after each new Reel so callers can save progress.
    """
    found: set[str] = set()
    seen_keys: list[int] = []

    scroll_to_oldest_message(page, max_scrolls)

    for _ in range(max_scrolls):
        # Back may re-render the chat, so re-read the screen after every Reel.
        while (state := chat_state(page)) and (
            target := next_unseen_reel(state, seen_keys)
        ):
            index, key = target
            seen_keys.append(key)  # mark first so a failure is not retried forever
            try:
                reel_url = open_reel_and_get_url(page, index)
            except Exception as error:
                print(f"Could not extract Reel URL: {error}")
                continue

            if reel_url:
                found.add(reel_url)
                print(f"Reel {len(found)}: {reel_url}")
                if on_url:
                    on_url(reel_url, sorted(found))

        state = chat_state(page)
        if state["top"] + state["client"] >= state["height"] - 5:
            break  # reached the newest message

        page.mouse.move(*chat_point(page))
        page.mouse.wheel(0, int(state["client"] * 0.8))
        page.wait_for_timeout(800)

    return sorted(found)
