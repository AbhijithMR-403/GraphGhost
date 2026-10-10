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
venv/bin/python -m pip install playwright
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

The script opens Instagram, clicks the Messages icon, selects the matching group, moves to the top of the conversation, and scrolls downward. On every pass it checks message links for Reel URLs, deduplicates them, and rewrites the output file with the URLs found so far. It keeps the browser open until Enter is pressed. It reports an error when the saved session is no longer logged in or the group is absent from the current inbox. Use `--max-scrolls` to increase the scan limit for a large conversation.

## Current status

- Working features: Persistent local browser profile, Messages navigation, exact-name group selection, and deduplicated Reel URL export.
- Known limitations: Instagram UI or login changes can break the browser selectors. The target group must already be visible in the inbox. Collection stops after `--max-scrolls`; verify the count for very large conversations. The script does not send messages.
- Libraries: [Playwright for Python](https://playwright.dev/python/). No datasets or external APIs are used.

See [AI_USAGE.md](AI_USAGE.md) for AI assistance and [CHANGELOG.md](CHANGELOG.md) for the development record.
