CREATE TABLE IF NOT EXISTS reels (
    code          TEXT PRIMARY KEY,
    url           TEXT NOT NULL,
    group_name    TEXT,
    caption       TEXT,
    author        TEXT,
    author_name   TEXT,
    posted_at     BIGINT,
    likes         INTEGER,
    comments      INTEGER,
    video_file    TEXT,
    collected_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    downloaded_at TIMESTAMPTZ
);
