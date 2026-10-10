
import argparse
import os
import re
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

from playwright.sync_api import sync_playwright

PROFILE_DIR = Path(".instagram_profile").resolve()
INSTAGRAM_URL = "https://www.instagram.com/"
REEL_PATH_PATTERN = re.compile(r"^/(?:reel|reels)/([^/?#]+)(?:/|$)")


def arguments() -> tuple[str, Path, int]:
    parser = argparse.ArgumentParser(
        description="Collect Instagram Reel URLs from a group conversation."
    )
    parser.add_argument(
        "--group",
        default=os.environ.get("INSTAGRAM_GROUP"),
        help="Exact group name (or set INSTAGRAM_GROUP).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reel_urls.txt"),
        help="Output file for unique Reel URLs (default: reel_urls.txt).",
    )
    parser.add_argument(
        "--max-scrolls",
        type=int,
        default=200,
        help="Maximum upward scrolls while loading older messages (default: 200).",
    )
    args = parser.parse_args()

    if not args.group:
        parser.error("provide --group GROUP_NAME or set INSTAGRAM_GROUP")
    if args.max_scrolls < 1:
        parser.error("--max-scrolls must be at least 1")

    return args.group, args.output, args.max_scrolls


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


def reel_url_from_href(href: str) -> str | None:
    """Return a canonical Reel URL for a matching Instagram href."""
    parsed = urlsplit(urljoin(INSTAGRAM_URL, href))
    if parsed.netloc not in {"instagram.com", "www.instagram.com"}:
        return None
    if parsed.path.startswith("/reels/audio/"):
        return None
    if not REEL_PATH_PATTERN.match(parsed.path):
        return None
    return urlunsplit(("https", "www.instagram.com", parsed.path, "", ""))


def collect_reel_urls(page, output_path: Path, max_scrolls: int) -> list[str]:
    """Harvest Reel links while scrolling downward through the conversation."""
    found: set[str] = set()

    page.evaluate(
        """
        () => {
            const scrollables = [document.scrollingElement, ...document.querySelectorAll('*')]
                .filter(element => element && element.scrollHeight > element.clientHeight + 20);
            for (const element of scrollables) {
                element.scrollTop = 0;
            }
        }
        """
    )
    page.wait_for_timeout(1_000)

    for _ in range(max_scrolls):
        hrefs = page.locator('a[href*="/reel"], a[href*="/reels"]').evaluate_all(
            "elements => elements.map(element => element.href)"
        )
        for href in hrefs:
            reel_url = reel_url_from_href(href)
            if reel_url:
                found.add(reel_url)
        write_urls(output_path, sorted(found))

        page.evaluate(
            """
            () => {
                const scrollables = [document.scrollingElement, ...document.querySelectorAll('*')]
                    .filter(element => element && element.scrollHeight > element.clientHeight + 20);
                for (const element of scrollables) {
                    element.scrollTop = Math.min(
                        element.scrollHeight - element.clientHeight,
                        element.scrollTop + Math.max(800, element.clientHeight * 0.8)
                    );
                }
            }
            """
        )
        viewport = page.viewport_size
        center_x = viewport["width"] // 2
        center_y = viewport["height"] // 2

        # Move the mouse to the center
        page.mouse.move(center_x, center_y)


        page.mouse.wheel(0, -1800)
        page.wait_for_timeout(500)

    return sorted(found)


def write_urls(output_path: Path, urls: list[str]) -> None:
    output_path.write_text("".join(f"{url}\n" for url in urls), encoding="utf-8")


def main() -> None:
    group_name, output_path, max_scrolls = arguments()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1280, "height": 900},
        )

        try:
            page = context.pages[0] if context.pages else context.new_page()
            open_group_conversation(page, group_name)
            urls = collect_reel_urls(page, output_path, max_scrolls)
            write_urls(output_path, urls)
            print(f'Found {len(urls)} unique Reel URL(s) in "{group_name}".')
            print(f"Saved URLs to {output_path.resolve()}")
            input("Press Enter to close the browser... ")
        finally:
            context.close()


if __name__ == "__main__":
    main()
