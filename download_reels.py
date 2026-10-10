import argparse
from pathlib import Path

from app.models import reels as reel_store
from app.models.migrate import apply_migrations
from app.scraper.downloader import download_reels



def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download Instagram Reels listed in a text file (one URL per line)."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("reel_urls.txt"),
        help="File with Reel URLs, as written by test.py (default: reel_urls.txt).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("downloads"),
        help="Folder for the .mp4 files (default: downloads).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Download again, overwriting files, even if the database marks them downloaded.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the browser window (default: headless).",
    )
    return parser.parse_args()


def main() -> None:
    args = arguments()
    if not args.input.exists():
        raise SystemExit(f"Input file not found: {args.input}")

    urls = [line.strip() for line in args.input.read_text().splitlines() if line.strip()]
    if not urls:
        raise SystemExit(f"No URLs in {args.input}")

    skipped = []
    if not args.force:
        try:
            apply_migrations()
            urls, skipped = reel_store.split_downloaded(urls)  # the database decides
        except RuntimeError as error:
            print(f"Warning: could not check Postgres, downloading everything. {error}")

    results = skipped
    if urls:
        results += download_reels(urls, args.output_dir, headless=not args.headed)
    saved = sum(result["ok"] for result in results)
    print(f"Downloaded or already downloaded: {saved} of {len(results)} Reel(s) in {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
