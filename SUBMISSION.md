# GraphGhost submission

## Project

- **Project name:** GraphGhost
- **Short description:** GraphGhost turns food Reels shared in an Instagram group into a searchable local food guide. It collects Reel URLs from a locally authenticated session, downloads and analyses the videos, stores verified Reel metadata and extracted places in Postgres, then lets people ask a chat interface for food recommendations with the supporting Reel links.
- **Code repository URL:** https://github.com/AbhijithMR-403/GraphGhost
- **Final submitted implementation commit SHA:** Pending — create and push the final implementation commit, then record its full SHA here before submission.
- **Working demo URL or local demo steps:** Run the FastAPI service and React client locally as described in [README.md](README.md#run-the-project). The web client is available at `http://127.0.0.1:5173`; the API and its interactive docs are at `http://127.0.0.1:8000` and `http://127.0.0.1:8000/docs`.
- **Demo access requirements:** A local Postgres database and a sanitized `.env` based on `.env.example` are required. Collecting or downloading Reels also needs a locally logged-in Instagram Playwright profile. Transcription, analysis, and chat answers need `OPENAI_API_KEY`; do not share any credentials with judges.

## Participants

| Participant name | GitHub handle | Contribution |
| --- | --- | --- |
| AbhijithMR-403 — confirm display name before submitting | [@AbhijithMR-403](https://github.com/AbhijithMR-403) | Project development and integration |

## Run and demonstrate

- **Prerequisites and versions:** Python 3.10+, PostgreSQL, Playwright Chromium, Node.js `^20.19.0` or `>=22.12.0`, and npm.
- **Install commands:**

  ```sh
  python3 -m venv venv
  venv/bin/python -m pip install -r requirements.txt
  venv/bin/python -m playwright install chromium
  cp .env.example .env
  cd client && npm install
  ```

- **Required environment variable names:** `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, and, for AI-powered processing and chat, `OPENAI_API_KEY`. Optional model overrides: `OPENAI_TRANSCRIBE_MODEL`, `OPENAI_ANALYSIS_MODEL`, and `OPENAI_CHAT_MODEL`.
- **Start commands:** From the project root, start the API with `venv/bin/python -m uvicorn app.main:app --reload`. In a second terminal, run `cd client && npm run dev`.
- **Demo walkthrough:**

  1. Start Postgres, copy `.env.example` to `.env`, and fill in local values.
  2. Start the API; its startup migration applies the SQL schema and starts the single job worker.
  3. If using fresh data, submit `POST /collect` in `/docs` with an exact Instagram group name, then follow the queued job through `GET /jobs/{job_id}`. The job can collect, download, transcribe, and analyse Reels.
  4. Open the React client and ask for a food type or place. GraphGhost returns matching analysed food spots, concise details and the original Instagram Reel links; use **Preview** to try the inline Reel embed.

- **Checks performed and results:** Python compilation checks and stubbed FastAPI/Postgres tests are recorded in [AI_USAGE.md](AI_USAGE.md). The React client passed `npm run lint` and `npm run build`; mocked-browser checks covered the chat layout, mobile width, links, errors, and price rendering. Live Instagram flows, live OpenAI requests, and Instagram embed rendering remain explicitly unverified where noted in the change log.
- **Known limitations or incomplete features:** Instagram UI selectors and saved-login behaviour can change; one local browser profile and in-process worker mean only one collection/download job should run at a time. The chatbot only searches Reels already collected, downloaded, and analysed. Reel embeds may be blocked by Instagram. There is no authentication for the local API, so it must not be exposed publicly. A hosted demo URL is not yet available.
- **Libraries, APIs, and public datasets used:** [Playwright for Python](https://playwright.dev/python/) for browser automation; [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/), [Psycopg](https://www.psycopg.org/), and [HTTPX](https://www.python-httpx.org/) for the API and Postgres access; [React](https://react.dev/) and [Vite](https://vite.dev/) for the web client; and the [OpenAI API](https://platform.openai.com/docs/overview) for transcription, Reel analysis, and chat. No public datasets are used.
- **AI usage record:** [AI_USAGE.md](AI_USAGE.md)
- **Development change log:** [CHANGELOG.md](CHANGELOG.md)

## Submission checklist

- [x] The project implementation started from scratch at the event.
- [ ] I participated solo or with no more than 4 team members in total — confirm participant details above.
- [x] Codex was used during development and its usage is documented.
- [x] The code repository URL and short description are provided; local demo instructions are provided in lieu of a hosted URL.
- [ ] README setup and demo instructions need a final reconciliation with the submission draft before submitting.
- [x] Actual checks and known limitations are documented.
- [x] Meaningful changes are documented throughout development; confirm the final set is committed before submitting.
- [ ] The final implementation is committed and pushed, and its SHA is recorded above.
- [x] No credentials or private data are included in the repository or demo instructions.
- [ ] The organizers' announced submission method and timing have been followed.

Event reference: [DevDay Exchange Community: Kochi on Luma](https://luma.com/z10nz8gp). The event wraps up by **10:00 AM IST on 11 October 2026**.
