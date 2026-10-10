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
