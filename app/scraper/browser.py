from pathlib import Path

# Holds the logged-in session; ignored by Git. Only one browser may use it at a time.
PROFILE_DIR = Path(".instagram_profile").resolve()


def launch_context(playwright, headless: bool = False):
    """Open Chromium with the saved Instagram login profile."""
    return playwright.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=headless,
        viewport={"width": 1280, "height": 900},
    )
