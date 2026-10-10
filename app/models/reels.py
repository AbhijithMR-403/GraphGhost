import os

import psycopg
from dotenv import load_dotenv
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

# Credentials come from the environment or a git-ignored .env file in the
# project root (see .env.example); nothing secret is stored in the code.
load_dotenv()

COLUMNS = (
    "code, url, group_name, caption, author, author_name, posted_at, likes, "
    "comments, video_path, collected_at, downloaded_at, transcript, transcribed_at"
)

def connection_info() -> str:
    """Build the connection string from the POSTGRES_* environment variables."""
    settings = {
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": os.environ.get("POSTGRES_PORT", "5432"),
        "dbname": os.environ.get("POSTGRES_DB", "graphghost"),
        "user": os.environ.get("POSTGRES_USER"),
        "password": os.environ.get("POSTGRES_PASSWORD"),
    }
    # Unset values are dropped so libpq falls back to its own defaults.
    return make_conninfo(**{key: value for key, value in settings.items() if value})


def connect() -> psycopg.Connection:
    """Open a short-lived connection; the API and the worker run in different threads."""
    try:
        connection = psycopg.connect(connection_info(), row_factory=dict_row, connect_timeout=5)
    except psycopg.OperationalError as error:
        raise RuntimeError(
            "Could not connect to Postgres. Check the POSTGRES_* values in .env "
            f"and that the database is running. Details: {error}"
        ) from error
    return connection


def code_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


def add_reel(url: str, group_name: str | None = None) -> None:
    """Remember a Reel; one that is already stored (and its details) is kept."""
    with connect() as db:
        db.execute(
            "INSERT INTO reels (code, url, group_name) VALUES (%s, %s, %s) "
            "ON CONFLICT (code) DO NOTHING",
            (code_from_url(url), url, group_name),
        )


def save_download(url: str, video_path: str, details: dict | None) -> None:
    """Record the downloaded file; details missing from this run keep their old values."""
    add_reel(url)
    details = details or {}
    with connect() as db:
        db.execute(
            """
            UPDATE reels SET video_path = %s, downloaded_at = now(),
                caption = COALESCE(%s, caption),
                author = COALESCE(%s, author),
                author_name = COALESCE(%s, author_name),
                posted_at = COALESCE(%s, posted_at),
                likes = COALESCE(%s, likes),
                comments = COALESCE(%s, comments)
            WHERE code = %s
            """,
            (
                video_path,
                details.get("caption"),
                details.get("author"),
                details.get("author_name"),
                details.get("posted_at"),
                details.get("likes"),
                details.get("comments"),
                code_from_url(url),
            ),
        )


ANALYSIS_COLUMNS = (
    "reel_code, reel_summary, language, restaurant_name, food_items, highlights, "
    "price_information, sentiment, confidence, needs_verification, analyzed_at"
)
LOCATION_COLUMNS = (
    "reel_code, location_name, full_address, locality, district, state, country, "
    "evidence, confidence, source"
)


def attach_analysis(db, reels: list[dict]) -> list[dict]:
    """Add an "analysis" entry (same shape the model returned) to each Reel, or None."""
    codes = [reel["code"] for reel in reels]
    analyses = {
        row.pop("reel_code"): row
        for row in db.execute(
            f"SELECT {ANALYSIS_COLUMNS} FROM reel_analysis WHERE reel_code = ANY(%s)", (codes,)
        )
    }
    for row in analyses.values():
        row["addresses"] = []
    for row in db.execute(
        f"SELECT {LOCATION_COLUMNS} FROM reel_locations WHERE reel_code = ANY(%s) "
        "ORDER BY reel_code, position",
        (codes,),
    ):
        analyses[row.pop("reel_code")]["addresses"].append(row)
    for reel in reels:
        reel["analysis"] = analyses.get(reel["code"])
    return reels


def list_reels(downloaded: bool | None = None) -> list[dict]:
    query = f"SELECT {COLUMNS} FROM reels"
    if downloaded is True:
        query += " WHERE video_path IS NOT NULL"
    elif downloaded is False:
        query += " WHERE video_path IS NULL"
    with connect() as db:
        rows = db.execute(query + " ORDER BY collected_at, code").fetchall()
        return attach_analysis(db, rows)


def get_reel(code: str) -> dict | None:
    with connect() as db:
        row = db.execute(f"SELECT {COLUMNS} FROM reels WHERE code = %s", (code,)).fetchone()
        return attach_analysis(db, [row])[0] if row else None


def split_downloaded(urls: list[str]) -> tuple[list[str], list[dict]]:
    """Split URLs into those still to download and results for those the database
    already marks as downloaded (video_path set). Files on disk are not consulted."""
    with connect() as db:
        stored = {
            row["code"]: row["video_path"]
            for row in db.execute("SELECT code, video_path FROM reels WHERE video_path IS NOT NULL")
        }
    pending, skipped = [], []
    for url in urls:
        path = stored.get(code_from_url(url))
        if path:
            skipped.append(
                {"url": url, "ok": True, "message": "Already downloaded (database).", "path": path}
            )
        else:
            pending.append(url)
    return pending, skipped


def list_needing_ai() -> list[dict]:
    """Downloaded Reels that still need a transcript, or an analysis of a non-empty one."""
    with connect() as db:
        return db.execute(
            """
            SELECT code, video_path, transcript FROM reels
            WHERE video_path IS NOT NULL
              AND (transcript IS NULL OR (
                    transcript <> ''
                    AND NOT EXISTS (SELECT 1 FROM reel_analysis a WHERE a.reel_code = reels.code)
              ))
            ORDER BY collected_at, code
            """
        ).fetchall()


def save_transcript(code: str, transcript: str) -> None:
    with connect() as db:
        db.execute(
            "UPDATE reels SET transcript = %s, transcribed_at = now() WHERE code = %s",
            (transcript, code),
        )


def text_or_none(value) -> str | None:
    return None if value is None else str(value)


def number_or_none(value) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def text_list(value) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def save_analysis(code: str, analysis: dict) -> None:
    """Store the model's JSON: one analysis row plus one row per candidate location."""
    price = analysis.get("price_information")
    needs_verification = analysis.get("needs_verification")
    addresses = [a for a in (analysis.get("addresses") or []) if isinstance(a, dict)]

    with connect() as db, db.transaction():
        db.execute(
            """
            INSERT INTO reel_analysis (
                reel_code, reel_summary, language, restaurant_name, food_items, highlights,
                price_information, sentiment, confidence, needs_verification
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (reel_code) DO UPDATE SET
                reel_summary = EXCLUDED.reel_summary, language = EXCLUDED.language,
                restaurant_name = EXCLUDED.restaurant_name, food_items = EXCLUDED.food_items,
                highlights = EXCLUDED.highlights, price_information = EXCLUDED.price_information,
                sentiment = EXCLUDED.sentiment, confidence = EXCLUDED.confidence,
                needs_verification = EXCLUDED.needs_verification, analyzed_at = now()
            """,
            (
                code,
                text_or_none(analysis.get("reel_summary")),
                text_or_none(analysis.get("language")),
                text_or_none(analysis.get("restaurant_name")),
                text_list(analysis.get("food_items")),
                text_list(analysis.get("highlights")),
                None if price is None else Jsonb(price),
                text_or_none(analysis.get("sentiment")),
                number_or_none(analysis.get("confidence")),
                needs_verification if isinstance(needs_verification, bool) else None,
            ),
        )
        db.execute("DELETE FROM reel_locations WHERE reel_code = %s", (code,))
        for position, address in enumerate(addresses):
            db.execute(
                """
                INSERT INTO reel_locations (
                    reel_code, position, location_name, full_address, locality, district,
                    state, country, evidence, confidence, source
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    code,
                    position,
                    text_or_none(address.get("location_name")),
                    text_or_none(address.get("full_address")),
                    text_or_none(address.get("locality")),
                    text_or_none(address.get("district")),
                    text_or_none(address.get("state")),
                    text_or_none(address.get("country")),
                    text_or_none(address.get("evidence")),
                    number_or_none(address.get("confidence")),
                    text_or_none(address.get("source")),
                ),
            )
