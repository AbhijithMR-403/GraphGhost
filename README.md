# GraphGhost

GraphGhost opens a locally authenticated Instagram session, navigates to Messages, selects a specified group conversation, and collects Reel links from the loaded conversation history. It is a small Playwright-based automation prototype built during the DevDay Exchange Community Hackathon: Kochi.

**[Event and registration on Luma](https://luma.com/z10nz8gp)** · **[Event rules](RULES.md)** · **[Agent instructions](AGENTS.md)**

## Event details

| Detail | Information |
| --- | --- |
| Venue | JAIN University, Kochi |
| Location | [Open the venue map](https://maps.app.goo.gl/Eme7gR7NDXSNRANu5) |
| Rooms | 2008 and 2009 |
| Check-in | 10 October 2026, 6:00 PM IST |
| Kick-off | 10 October 2026, 6:30 PM IST |
| Wrap-up | 11 October 2026, by 10:00 AM IST |
| Participation | Solo or a team of up to 4 participants |
| Theme | Open — build anything you like |

Keep your approved Luma QR code ready for entry, and bring your laptop and charger. Eligible checked-in participants will receive Codex credits and OpenAI API credits.

## Run the project

Prerequisites: Python 3.10+ and the Playwright Python package with Chromium installed.

```bash
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
venv/bin/python -m playwright install chromium
```

The browser profile lives in `.instagram_profile/` and is deliberately ignored by Git because it can contain session credentials. Log in to Instagram in that profile once before running the automation; later runs reuse the stored session.

Open a group by giving its exact visible name:

```bash
venv/bin/python test.py --group "Example Group"
```

The command saves one canonical URL per Reel to `reel_urls.txt`. Choose another output file with `--output`:

```bash
venv/bin/python test.py --group "Example Group" --output reels.txt
```

Or set the name through an environment variable:

```bash
INSTAGRAM_GROUP="Example Group" venv/bin/python test.py
```

The script opens Instagram, clicks the Messages icon, selects the matching group, and scrolls up to the oldest message. It then walks down one screen at a time: on each screen it clicks every Reel message not yet handled, reads the `/reel/<code>/` URL from the address bar, goes back to the chat, and rewrites the output file after every Reel. Every run scans the whole conversation; Reels already in Postgres are kept and are not downloaded again. When collection finishes the browser closes and every collected Reel is downloaded to `downloads/<code>.mp4` (change the folder with `--download-dir`, skip downloading with `--no-download`; a Reel is skipped when the database already has its `video_path`; an existing file on disk is overwritten). It closes Instagram's notification pop-ups, scrolls the inbox list to find the group, and confirms a conversation really opened. On an error it prints the message (including the page it was on) and leaves the window open until you press Enter. It reports an error when the saved session is no longer logged in or the group is absent from the inbox. Run only one thing at a time: the CLI and the API share `.instagram_profile`, and two browsers on it collide. Use `--max-scrolls` to bound both the scroll to the oldest message and the walk down for a large conversation. The CLI also saves the Reels, their details and each video's relative path to Postgres when the database is reachable; otherwise it prints a warning and keeps the files only.

### Download the Reels

After `test.py` has written the URLs, download the videos with the same saved login profile:

```sh
venv/bin/python download_reels.py --input reel_urls.txt --output-dir downloads
```

Each Reel is saved as `downloads/<code>.mp4`; a Reel is skipped when the database already has its `video_path` (files on disk are not checked and are overwritten when downloaded); add `--force` to download again regardless. If Postgres is unreachable it warns and downloads everything. Add `--headed` to watch the browser. Close any other browser using `.instagram_profile` first. The script reads the video URL from the data the Reel page loads, so it needs the profile to be logged in; Instagram rejects unauthenticated requests.

### API

The same collection and download are available as a FastAPI app (`app/main.py`; scraping code in `app/scraper/`, Postgres store in `app/models/reels.py`, job queue in `app/workers/tasks.py`). Run it from the project root:

```sh
venv/bin/python -m uvicorn app.main:app --reload
```

Postgres must be running and the credentials must be in a `.env` file in the project root (ignored by Git). Copy the sanitized example and fill in your values:

```sh
cp .env.example .env
```

| Key | Meaning | Default if unset |
| --- | --- | --- |
| `POSTGRES_HOST` | Database host | `localhost` |
| `POSTGRES_PORT` | Database port | `5432` |
| `POSTGRES_DB` | Database name (create it first, e.g. `createdb graphghost`) | `graphghost` |
| `POSTGRES_USER` | Database user | your OS user |
| `POSTGRES_PASSWORD` | Database password | none |

Transcription and analysis also need an OpenAI key in `.env`:

| Key | Meaning | Default if unset |
| --- | --- | --- |
| `OPENAI_API_KEY` | OpenAI API key (required for transcription) | none; the transcribe job fails with a clear message |
| `OPENAI_TRANSCRIBE_MODEL` | Model for `/v1/audio/transcriptions` | `gpt-transcribe` |
| `OPENAI_ANALYSIS_MODEL` | Model for `/v1/responses` | `gpt-6-luna` |

Real environment variables take precedence over `.env`.

Database changes are plain SQL files in `migrations/`, applied in name order and recorded in the `schema_migrations` table. The API applies pending ones at startup; to apply them by hand:

```sh
venv/bin/python -m app.models.migrate
```

To change the schema, add the next numbered file (never edit one that has already been applied), for example `migrations/0002_add_duration.sql`:

```sql
ALTER TABLE reels ADD COLUMN duration_seconds INTEGER;
```

Then run the command above (or restart the API). Each file runs in its own transaction, so a failing file changes nothing. There is no automatic rollback; write a new migration to undo a change.

Requests return a `job_id` immediately. Jobs go on an in-process queue and run one at a time, because collecting and downloading share one logged-in browser profile.

| Endpoint | Purpose |
| --- | --- |
| `POST /collect` with `{"group": "Example Group"}` | Queue a collection. Optional `max_scrolls`, `headless`, `download` (default `true`: queue a download of new Reels when collection finishes) and `transcribe` (default `true`: transcribe and analyse them after the download). |
| `POST /download` with `{}` or `{"urls": [...]}` | Queue a download of the given URLs, or of every collected Reel not downloaded yet. The database decides what counts as downloaded (`video_path` set); existing files are overwritten. `"force": true` downloads again regardless. Files go to `downloads/<code>.mp4`. Unless `"transcribe": false`, downloaded Reels with no transcript or analysis are then transcribed and analysed and stored; this also happens when there is nothing left to download. The job only fails when nothing is left to download or process. |
| `POST /transcribe` | Queue transcription and analysis of downloaded Reels that have no transcript or analysis yet. |
| `GET /jobs`, `GET /jobs/{job_id}` | `status` (`queued`, `running`, `done`, `failed`), progress in `results`, and any `error`. |
| `GET /reels?downloaded=true\|false` | Every collected Reel with details. |
| `GET /reels/{code}` | One Reel. Downloaded Reels carry `video_path` (relative to the project root, e.g. `downloads/<code>.mp4`) and `video_url` (`/downloads/<code>`). |
| `GET /downloads`, `GET /downloads/{code}` | List downloaded files; stream one video, located through the `video_path` stored in the database. The code may be given with or without `.mp4`. |
| `GET /chat` | A chat page: ask for a food spot and get matching places with details and Reel links. |
| `POST /chat` with `{"message": "...", "history": [...]}` | Same as the page, as JSON: returns `answer`, `spots` (restaurant, food, places, price, reason, `url`) and a Markdown `reply`. `history` is optional (`{"role": "user"|"assistant", "content": "..."}`, last 6 turns used). |
| `GET /health` | Liveness check. Interactive docs are at `/docs`. |

The chatbot searches the analysed Reels (restaurant, food, location, price, caption), sends the best matches to the model (`OPENAI_CHAT_MODEL`, optional; defaults to `OPENAI_ANALYSIS_MODEL`) and shows the spots it picks. Details and links are taken from the database, never from the model, so a Reel link is always `https://www.instagram.com/reel/<code>/`; a code the model invents is dropped. It only knows Reels that have been collected, downloaded and analysed.

Where data lives:

- Postgres table `reels`: one row per Reel — `code`, `url`, `group_name`, `caption`, `author`, `author_name`, `posted_at` (Unix seconds), `likes`, `comments`, `video_path`, `collected_at`, `downloaded_at` (both timestamps with time zone). Collections accumulate: a Reel already stored is kept, not replaced.
- `reel_urls.txt`: every collected URL, rewritten from the database after each collection.
- `downloads/<code>.mp4`: the videos (ignored by Git).

Each downloaded Reel is then transcribed (`reels.transcript`) and analysed. The model's JSON is stored in two tables:

- `reel_analysis`: one row per Reel with `reel_summary`, `language`, `restaurant_name`, `food_items` and `highlights` (text arrays), `price_information` (JSONB), `sentiment`, `confidence`, `needs_verification`, `analyzed_at`.
- `reel_locations`: one row per candidate location, any number per Reel, ordered by `position`: `location_name`, `full_address`, `locality`, `district`, `state`, `country`, `evidence`, `confidence`, `source`. Conflicting candidates stay separate rows.

`GET /reels` and `GET /reels/{code}` return these assembled back into the model's original shape under `analysis` (with `addresses` as a list), or `null` when not analysed yet. Reels that already have a transcript and analysis are never sent to OpenAI again. Silent videos get an empty transcript and no analysis.

Caption, author, likes and comments are read from Instagram's page data when a Reel is downloaded, so they stay empty until then and are a snapshot of that moment. Jobs are kept in memory and are lost on restart; the database and files persist. Transcription and analysis are not part of the API yet.

### Chat UI

`client/` is a React (Vite) app with a minimal white chat page for the food-spot chatbot. Each recommended place appears as a card with its details and its Instagram Reel link, plus a **Preview** button that embeds the Reel inline (Instagram may refuse to render the embed for some Reels; the link always works).

```sh
cd client
npm install        # first time only
npm run dev        # http://127.0.0.1:5173
```

Start the API first (`venv/bin/python -m uvicorn app.main:app --reload` from the project root). In development Vite forwards `/api/...` to `http://127.0.0.1:8000`, so no CORS setup is needed. To point the page at another API address, set `VITE_API_URL` (for example in `client/.env.local`). `npm run build` writes a static build to `client/dist`; it must be served from somewhere that can reach the API at `VITE_API_URL`.

## Current status

- Working features: Persistent local browser profile, Messages navigation, exact-name group selection, and deduplicated Reel URL export.
- Known limitations: Instagram UI or login changes can break the browser selectors. The target group must already be visible in the inbox. Collection stops after `--max-scrolls`; verify the count for very large conversations. The script does not send messages.
- Libraries: [Playwright for Python](https://playwright.dev/python/). No datasets or external APIs are used.

See [AI_USAGE.md](AI_USAGE.md) for AI assistance and [CHANGELOG.md](CHANGELOG.md) for the development record.
