from pathlib import Path

from playwright.sync_api import sync_playwright

from app.scraper.browser import launch_context
from app.scraper.instagram import collect_reel_urls, open_group_conversation


def write_urls(output_path: Path, urls: list[str]) -> None:
    output_path.write_text("".join(f"{url}\n" for url in urls), encoding="utf-8")


def collect_group_reels(
    group_name: str,
    output_path: Path,
    max_scrolls: int,
    headless: bool,
    on_url=None,
) -> list[str]:
    """Open the group, collect every Reel URL, and save them to output_path."""

    def save_progress(url: str, urls: list[str]) -> None:
        write_urls(output_path, urls)  # checkpoint after every Reel
        if on_url:
            on_url(url, urls)

    with sync_playwright() as p:
        context = launch_context(p, headless=headless)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            open_group_conversation(page, group_name)
            urls = collect_reel_urls(page, max_scrolls, on_url=save_progress)
        finally:
            context.close()

    write_urls(output_path, urls)
    return urls
