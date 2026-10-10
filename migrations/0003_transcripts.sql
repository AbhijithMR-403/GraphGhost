ALTER TABLE reels
    ADD COLUMN transcript     TEXT,
    ADD COLUMN transcribed_at TIMESTAMPTZ,
    ADD COLUMN analysis       JSONB,
    ADD COLUMN analyzed_at    TIMESTAMPTZ;
