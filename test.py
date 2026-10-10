
import argparse
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

from app.scraper.browser import launch_context
from app.models import reels as reel_store
from app.models.migrate import apply_migrations
from app.scraper.collector import write_urls
from app.scraper.downloader import download_reels
from app.scraper.instagram import collect_reel_urls, open_group_conversation


def arguments() -> argparse.Namespace:
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
        help="Maximum downward scrolls through the conversation (default: 200).",
    )
    parser.add_argument(
        "--download-dir",
        type=Path,
        default=Path("downloads"),
        help="Folder for the downloaded videos (default: downloads).",
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Only collect URLs; do not download the videos afterwards.",
    )
    args = parser.parse_args()

    if not args.group:
        parser.error("provide --group GROUP_NAME or set INSTAGRAM_GROUP")
    if args.max_scrolls < 1:
        parser.error("--max-scrolls must be at least 1")

    return args


def database_available() -> bool:
    """Migrate and check Postgres; on failure say so and carry on with files only."""
    try:
        apply_migrations()
        return True
    except RuntimeError as error:
        print(f"Warning: results will not be saved to Postgres. {error}")
        return False


def main() -> None:
    args = arguments()
    use_database = database_available()

    def remember_url(url: str, urls: list[str]) -> None:
        write_urls(args.output, urls)
        if use_database:
            reel_store.add_reel(url, args.group)

    def remember_download(result: dict, results: list[dict]) -> None:
        if use_database and result["ok"] and result["path"]:
            reel_store.save_download(result["url"], result["path"], result["details"])

    with sync_playwright() as p:
        context = launch_context(p, headless=False)

        try:
            page = context.pages[0] if context.pages else context.new_page()
            open_group_conversation(page, args.group)
            urls = collect_reel_urls(
                page,
                args.max_scrolls,
                on_url=remember_url,
            )
            write_urls(args.output, urls)
        finally:
            context.close()  # the download below needs the same browser profile

    print(f'Found {len(urls)} unique Reel URL(s) in "{args.group}".')
    print(f"Saved URLs to {args.output.resolve()}")

    if args.no_download or not urls:
        return

    results = download_reels(
        urls, args.download_dir, headless=True, on_result=remember_download
    )
    saved = sum(result["ok"] for result in results)
    print(f"Downloaded or found {saved} of {len(urls)} Reel(s) in {args.download_dir.resolve()}")


if __name__ == "__main__":
    main()
