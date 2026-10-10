"""Apply the SQL files in migrations/ that have not run yet.

Run by hand with `python -m app.models.migrate`; the API also runs it at startup.
Files are applied in name order, each in its own transaction, and recorded in
the schema_migrations table, so running it again is safe.
"""

from pathlib import Path

from app.models.reels import connect

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def apply_migrations() -> list[str]:
    """Apply pending migrations; return the names that were applied."""
    applied = []
    with connect() as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        done = {row["version"] for row in db.execute("SELECT version FROM schema_migrations")}

        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in done:
                continue
            with db.transaction():
                db.execute(path.read_text(encoding="utf-8"))
                db.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.name,))
            applied.append(path.name)
    return applied


if __name__ == "__main__":
    names = apply_migrations()
    print("Applied: " + ", ".join(names) if names else "Database is up to date.")
