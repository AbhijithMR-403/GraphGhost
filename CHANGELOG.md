# Change log

Record each meaningful project change during the event, newest first. Update this file in the same commit as the change. Use a real timestamp with timezone, for example `YYYY-MM-DDTHH:MM:SS+05:30`.

## Event build log

## 2026-10-10T23:31:58+0530 — Export Reel URLs from group conversations

- Changed: Added Reel URL harvesting, deduplication, bounded upward scrolling, and configurable output in `test.py`; updated `README.md` and `AI_USAGE.md`.
- Why: Export the URLs of Reels shared in a selected Instagram group.
- Validation: Python syntax compilation completed; live Instagram verification remains pending because it requires an authenticated account and a real group.
- Limitations: Instagram selectors and message loading behavior may change; very large conversations may require a higher `--max-scrolls` value.

## 2026-10-10T23:53:49+0530 — Scroll downward and checkpoint Reel URLs

- Changed: The conversation scan now starts at the top, scrolls downward, and writes deduplicated Reel URLs after every scan pass.
- Why: Make the scan direction explicit and preserve URLs as they are discovered.
- Validation: `python3 -m py_compile test.py` passed; live Instagram verification remains pending.
- Limitations: Instagram UI and virtualized message loading may still affect which messages are exposed to Playwright.

## 2026-10-11T01:12:44+0530 — Extract Reel URLs from Clip buttons

- Changed: Added current/new-tab URL extraction for Clip buttons, cleanup of tabs opened by the click, and return navigation to the group.
- Why: Some Instagram Reel messages expose a Clip button instead of a direct anchor URL.
- Validation: `python3 -m py_compile test.py` passed; live Instagram verification remains pending.
- Limitations: The Clip-button selector depends on Instagram's current accessibility markup.

## 2026-10-11T01:20:00+0530 — Fix Playwright timeout import

- Changed: Imported Playwright's `TimeoutError` with the local alias `PlaywrightTimeoutError`.
- Why: The installed Playwright version does not export a class named `PlaywrightTimeoutError`.
- Validation: Python syntax compilation passed; runtime verification remains pending.
- Limitations: None identified for this import correction.

The implementation record above replaces the initial documentation-only placeholder.

```text
## <actual timestamp> — <short change title>

- Changed: <feature or files changed>
- Why: <reason for the change>
- Validation: <commands or manual checks actually run, with results>
- Limitations: <known issues or "None identified in these checks">
```

## Template setup — 10 October 2026

- Changed: Added the event README, rules, agent guide, change log, AI usage record, submission checklist, Git ignore rules, and pull request checklist.
- Why: Give participants a consistent starting point for event rules, basic coding patterns, documented changes, and regular commits.
- Validation: Checked local Markdown links, event detail consistency, required documents, and diff whitespace before publishing.
- Limitations: Documentation scaffolding only; no participant project, application, or working demo is included. GitHub publication and template status are verified separately after creation.

## 2026-10-11T01:25:00+0530 — Click each Reel in the group and store its URL

- Changed: `collect_reel_urls` in `test.py` now scrolls up to load the full conversation, then clicks each Reel (Clip) bubble in order, reads the `/reel/<code>/` URL, goes back with browser Back, and checkpoints the output file after every Reel. Removed the link-scraping and downward-scroll logic.
- Why: Clicking a Reel in the chat changes the page URL, and Back returns to the chat; this matches the behavior observed by the user.
- Validation: `venv/bin/python -m py_compile test.py` passed; live Instagram verification remains pending.
- Limitations: Relies on the `svg[aria-label="Clip"]` marker; if Back resets the chat scroll, history is reloaded, which is slow for long chats. `--max-scrolls` bounds each history load.

## 2026-10-11T01:45:00+0530 — Process Reels page by page from the oldest message

- Changed: `collect_reel_urls` in `test.py` now scrolls to the oldest message, then walks down one screen at a time, opening every unseen Reel bubble on screen, going back, and continuing. Reels are identified by their offset inside the chat scroll pane instead of by index.
- Why: The previous run stored only the top Reel; Instagram keeps only nearby messages in the page, so preloading the whole history and clicking by index missed the rest. The user confirmed Back keeps the scroll position.
- Validation: `venv/bin/python -m py_compile test.py` passed; live Instagram verification remains pending.
- Limitations: Depends on `svg[aria-label="Clip"]` and on the chat pane being the scrollable element at 75% of the window width; a Reel only partly on screen is picked up on the next screen.

## 2026-10-11T02:10:00+0530 — Add Reel downloader

- Changed: Added `download_reels.py`, which reads Reel URLs from a text file, opens each in the saved logged-in browser profile, reads `video_versions[].url` from the JSON the page loads, and saves `downloads/<code>.mp4`. Added `downloads/` and `.instagram_profile/` to `.gitignore`.
- Why: Download the Reels collected by `test.py`. The no-login GraphQL method from the referenced Medium article could not be read (HTTP 403 from Medium) and a direct unauthenticated GraphQL request returned HTTP 403 from Instagram on 2026-10-11, so the downloader uses the logged-in profile instead.
- Validation: `venv/bin/python -m py_compile download_reels.py` passed; a download has not been run end to end.
- Limitations: Requires a logged-in saved profile; depends on Instagram still exposing `video_versions` in its JSON responses; fails if the profile is open in another browser window.

## 2026-10-11T02:30:00+0530 — Fix downloader saving the wrong Reels

- Changed: `download_reels.py` now accepts a video only from the media object whose `code`/`shortcode` equals the requested Reel's code.
- Why: The first version took the first `video_versions` in any response, which could belong to a suggested Reel loaded by the page.
- Validation: `venv/bin/python -m py_compile download_reels.py` passed; not re-run against Instagram.
- Limitations: Files already in `downloads/` from the earlier version may be wrong and are skipped as "already downloaded"; delete them before re-running.

## 2026-10-11T02:55:00+0530 — Fix "No video found" in the downloader

- Changed: `download_reels.py` now parses JSON embedded in the page HTML (`<script type="application/json">`) and every XHR/fetch response from instagram.com, regardless of content type.
- Why: Instagram labels its `graphql/query` response `text/javascript` and embeds the Reel data in the HTML, so the content-type filter discarded the data.
- Validation: `venv/bin/python -m py_compile` passed; downloaded `DalOdO-vQ_p` and `DbQ1oHIzQ0Y` (the two failing Reels) as valid MP4 files (`file` reports ISO Media). Playback and that each video is the intended Reel were not checked by a person.
- Limitations: Depends on Instagram's current page data layout and a logged-in profile.

## 2026-10-11T03:20:00+0530 — Add a simple FastAPI app

- Changed: Added `app/main.py` (`POST /collect`, `GET /jobs/{id}`, `GET /reels`, `GET /health`) and moved the scraping logic out of `test.py` into `app/scraper/{browser,instagram,collector}.py`; `test.py` is now a thin CLI over it. Added `requirements.txt`.
- Why: Expose Reel collection over HTTP using the project layout the user provided, without duplicating the scraper.
- Validation: All modules compile; endpoints exercised with FastAPI's test client against a stubbed scraper (validation 422, success, failure, 404). A real collection through the API and the refactored `test.py` CLI were not run against Instagram.
- Limitations: In-memory jobs; one collection at a time; no transcription, analysis, database or download endpoint yet (`services/`, `models/`, `workers/` from the layout were intentionally not created).

## 2026-10-11T03:50:00+0530 — Add download endpoints and a job queue to the API

- Changed: Added `app/scraper/downloader.py` (logic moved from `download_reels.py`, which is now a thin CLI), `app/workers/tasks.py` (in-process queue with one worker thread), and the endpoints `POST /download`, `GET /jobs`, `GET /downloads`, `GET /downloads/{code}`. `POST /collect` now queues instead of returning 409 when busy.
- Why: Expose downloads over HTTP; collection and download share one browser profile, so jobs are serialized through a queue. An external broker (Redis/Celery) was judged unnecessary for a single user and a single profile.
- Validation: Modules compile; endpoints and queue ordering exercised with FastAPI's test client against stubbed scraper functions (queued -> running order, failed job does not block the next, path-traversal rejected); the refactored `download_reels.py` downloaded two real Reels as valid MP4 files. A real collection and a real download through the API were not run.
- Limitations: Jobs and queue are in memory (lost on restart, no retries); one worker; no authentication on the API, so run it locally only.

## 2026-10-11T04:25:00+0530 — Store Reel details, accumulate URLs, auto-download after collection

- Changed: Added `app/models/reels.py` (SQLite `graphghost.db`); the downloader now also extracts caption, author, post time, likes and comments; `POST /collect` queues a download of new Reels by default (`download: false` disables it); `POST /download` with no URLs downloads every collected Reel not yet downloaded; `GET /reels` returns Reels with details and `GET /reels/{code}` returns one; `reel_urls.txt` is rewritten from the database so it accumulates across runs. `GET /reels` now returns `{"reels": [...]}` instead of `{"urls": [...]}`.
- Why: The user asked for stored Reel details, merged results across collections, and downloading to start when collection finishes.
- Validation: Modules compile; an end-to-end API test with collection stubbed and the download/details live ran against two real Reels: auto-download queued and finished, details were stored (author, caption, likes, comments, posted_at), a second collection merged without duplicates and downloaded only the new Reel, and unknown codes returned 404. A real group collection through the API was not run.
- Limitations: Details are filled only at download time and are a snapshot; Instagram may change field names; jobs and the queue are in memory; no authentication on the API; `test.py` CLI still overwrites its chosen `--output` file with only that run's URLs and does not write to the database.

## 2026-10-11T05:05:00+0530 — Move the Reel store from SQLite to Postgres

- Changed: `app/models/reels.py` now uses Postgres through `psycopg`, configured by `DATABASE_URL` (default `postgresql://localhost/graphghost`); the table is created on first use; timestamps are `timestamptz`. Added `docker-compose.yml` for a local database and `psycopg[binary]` to `requirements.txt`. Removed the unused SQLite ignore entry.
- Why: The user asked for Postgres.
- Validation: Re-ran the end-to-end API test (collection stubbed, real downloads and details for two Reels) against a throwaway Postgres 18 cluster: rows, merge behaviour, filters and 404s matched the SQLite run, and `psql` showed both rows with details. `docker-compose.yml` was not started; the default local URL was not tried against a Homebrew service.
- Limitations: No migration from any earlier `graphghost.db` (none existed outside tests); a new connection per call, no pooling; the Compose database uses trust authentication and is for local development only.

## 2026-10-11T05:30:00+0530 — Read Postgres credentials from .env; drop Docker Compose

- Changed: `app/models/reels.py` builds the connection from `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER` and `POSTGRES_PASSWORD`, loaded from the environment or a project-root `.env` via `python-dotenv`; `DATABASE_URL` is no longer used. Added `.env.example` (placeholders only), added `python-dotenv` to `requirements.txt`, removed `docker-compose.yml` and the Docker instructions.
- Why: The user does not want Docker for now and wants credentials kept in `.env`.
- Validation: Compiled; with a temporary `.env` (since deleted) pointing at a throwaway Postgres 18 cluster, with a password containing a space and `@`, the module connected, created the table, and stored and listed a Reel. The throwaway cluster was stopped afterwards.
- Limitations: Missing or wrong credentials surface as a job failure or a 500 on `/reels` with a message naming the `POSTGRES_*` values; connections are not pooled.

## 2026-10-11T06:00:00+0530 — Add SQL migrations

- Changed: Added `migrations/0001_create_reels.sql` and `app/models/migrate.py` (applies pending `migrations/*.sql` in name order, one transaction each, tracked in `schema_migrations`). The API runs it at startup and `python -m app.models.migrate` runs it by hand. Removed the inline `CREATE TABLE` from `app/models/reels.py`.
- Why: Schema changes need to be repeatable and reviewable; `CREATE TABLE IF NOT EXISTS` cannot alter an existing table.
- Validation: Against a throwaway Postgres 18 cluster: applying to a database that already had the table, to a fresh database, re-running (no-op), and adding a second migration (applied once, column added). The API startup path was compiled but not started.
- Limitations: Forward-only (no down migrations); no checksum to detect an edited, already-applied file; no locking, so run one migrator at a time. A tool such as Alembic would be worth adopting if the schema grows.

## 2026-10-11T06:25:00+0530 — Download Reels after collection in the CLI

- Changed: `test.py` now closes the collection browser and then downloads every collected Reel with `app.scraper.downloader.download_reels`. Added `--download-dir` and `--no-download`. Removed the "Press Enter to close the browser" pause.
- Why: The user wants Reels downloaded once they have been fetched, as the API already does.
- Validation: `venv/bin/python -m py_compile test.py` passed and the argument parser was exercised (`--help`). A full run against a real group was not performed; the download step itself was verified earlier on two real Reels.
- Limitations: The CLI saves files only and does not store details in Postgres; the download starts only after the whole collection finishes.

## 2026-10-11T06:55:00+0530 — Store the relative video path in Postgres and serve it through the API

- Changed: Migration `0002_video_path.sql` renames `reels.video_file` to `video_path` and prefixes existing bare file names with `downloads/`. Downloads now record the path relative to the project root (for example `downloads/<code>.mp4`). `GET /reels` and `GET /reels/{code}` return `video_path` and a `video_url` (`/downloads/<code>`); `GET /downloads/{code}` streams the file found through the stored path (falling back to the downloads folder) and refuses paths outside the project. `test.py` now also saves Reels, details and paths to Postgres, with a warning and files-only fallback when the database is unreachable. A re-download no longer overwrites stored details with NULL.
- Why: The user asked for the relative path to be stored in the database and be reachable through the API.
- Validation: Migration backfill checked on old-style rows (bare name prefixed, NULL and already-pathed values untouched); API end to end against a throwaway Postgres 18 with real downloads of two Reels (path stored as `downloads_test/<code>.mp4`, `GET /reels/{code}` shows `video_path` and `video_url`, `GET /downloads/{code}` returned 200 `video/mp4`, unknown code 404). The CLI changes were compiled only; a full CLI run against a real group was not performed.
- Limitations: Paths are relative to the directory the app runs from, so run it from the project root; a custom `--download-dir` outside the project cannot be served by the API; the migration is forward-only.

## 2026-10-11T03:50:00+0530 — Accept .mp4 in the download URL

- Changed: `GET /downloads/{code}` now also accepts `<code>.mp4`.
- Why: `/downloads/DalOdO-vQ_p.mp4` returned "Invalid Reel code" because only the bare code was accepted.
- Validation: `venv/bin/python -m py_compile app/main.py` passed; `/downloads/DalOdO-vQ_p`, `/downloads/DalOdO-vQ_p.mp4` and invalid inputs checked with FastAPI's test client against the real database (read-only).
- Limitations: None known.

## 2026-10-11T04:10:00+0530 — Transcribe and analyse downloaded Reels with OpenAI

- Changed: Added `app/services/transcription.py` (`POST /v1/audio/transcriptions` with the Malayalam/Kerala prompt), `app/services/reel_analysis.py` (`POST /v1/responses` with the food-discovery extraction prompt; reply parsed and checked for the required keys), `app/services/openai_api.py` (key and error handling), migration `0003_transcripts.sql` (`transcript`, `transcribed_at`, `analysis` JSONB, `analyzed_at`), a `transcribe` job in `app/workers/tasks.py`, `POST /transcribe`, and a `transcribe` option (default true) on `/collect` and `/download`. After a download job, a transcribe job is queued only when a downloaded Reel has no transcript (or a non-empty transcript with no analysis). Added `httpx` to `requirements.txt` and the OpenAI keys to `.env.example`.
- Why: The user asked for downloaded Reels to be transcribed, once, and the transcript analysed.
- Validation: Against a throwaway Postgres 18 with OpenAI HTTP calls stubbed: requests carried the bearer key, model, prompt and transcript; a Reel with an existing transcript and analysis was skipped; a silent video got an empty transcript and no analysis; a fenced JSON reply was parsed; a missing key failed the job with a clear message; the chain collect, download, transcribe ran automatically and a repeat collect created no new jobs or API calls. No real OpenAI request was made, so the model names `gpt-transcribe` and `gpt-6-luna` and the real response shape are unverified.
- Limitations: A Reel whose transcription or analysis fails is retried on the next run (and billed again); transcripts are not chunked, so videos over the API's upload size limit fail with the API's message; the Cloudflare cookies in the supplied curl commands are not sent; manual `POST /transcribe` with nothing pending ends as a failed job.

## 2026-10-11T04:40:00+0530 — Store analysis in normalised tables with multiple locations per Reel

- Changed: Migration `0004_analysis_tables.sql` creates `reel_analysis` (one row per Reel) and `reel_locations` (many rows per Reel, ordered by `position`), converts any analysis already stored in `reels.analysis` into them, then drops `reels.analysis` and `reels.analyzed_at`. `save_analysis` writes both tables in one transaction and replaces a Reel's previous locations on re-save; `GET /reels` and `GET /reels/{code}` rebuild the original JSON shape under `analysis`. The "needs analysis" check now looks for a missing `reel_analysis` row.
- Why: The user wanted the analysis JSON as proper tables, with support for more than one location per Reel.
- Validation: On a throwaway Postgres 18: the user's sample JSON migrated into one analysis row and one location row with every field intact (including Malayalam evidence text); malformed stored JSON (string confidence, scalar `food_items`, non-object address, empty array, nulls) migrated without error, with unusable values set to NULL; saving three locations and re-saving with one left exactly one; the reassembled API shape had all ten keys plus `analyzed_at`.
- Limitations: Raw model output is no longer kept, so unexpected extra keys the model returns are dropped; `price_information` stays free-form JSONB; the migration is forward-only (dropped columns are not restored); no endpoint searches locations across Reels yet.
