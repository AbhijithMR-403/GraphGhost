-- One row per analysed Reel.
CREATE TABLE reel_analysis (
    reel_code          TEXT PRIMARY KEY REFERENCES reels(code) ON DELETE CASCADE,
    reel_summary       TEXT,
    language           TEXT,
    restaurant_name    TEXT,
    food_items         TEXT[] NOT NULL DEFAULT '{}',
    highlights         TEXT[] NOT NULL DEFAULT '{}',
    price_information  JSONB,            -- free-form: mentioned prices or offers
    sentiment          TEXT,
    confidence         DOUBLE PRECISION, -- overall extraction confidence, 0 to 1
    needs_verification BOOLEAN,
    analyzed_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Any number of candidate locations per Reel, in the order the model gave them.
CREATE TABLE reel_locations (
    id            BIGSERIAL PRIMARY KEY,
    reel_code     TEXT NOT NULL REFERENCES reels(code) ON DELETE CASCADE,
    position      INTEGER NOT NULL,
    location_name TEXT,
    full_address  TEXT,
    locality      TEXT,
    district      TEXT,
    state         TEXT,
    country       TEXT,
    evidence      TEXT,                  -- quoted transcript text
    confidence    DOUBLE PRECISION,      -- 0 to 1
    source        TEXT,                  -- transcript, visual or both
    UNIQUE (reel_code, position)
);
CREATE INDEX reel_locations_reel_code_idx ON reel_locations (reel_code);

-- Move analyses stored by migration 0003 into the new tables.
INSERT INTO reel_analysis (
    reel_code, reel_summary, language, restaurant_name, food_items, highlights,
    price_information, sentiment, confidence, needs_verification, analyzed_at
)
SELECT
    code,
    analysis->>'reel_summary',
    analysis->>'language',
    analysis->>'restaurant_name',
    CASE WHEN jsonb_typeof(analysis->'food_items') = 'array'
         THEN ARRAY(SELECT jsonb_array_elements_text(analysis->'food_items')) ELSE '{}' END,
    CASE WHEN jsonb_typeof(analysis->'highlights') = 'array'
         THEN ARRAY(SELECT jsonb_array_elements_text(analysis->'highlights')) ELSE '{}' END,
    NULLIF(analysis->'price_information', 'null'::jsonb),
    analysis->>'sentiment',
    CASE WHEN jsonb_typeof(analysis->'confidence') = 'number'
         THEN (analysis->>'confidence')::double precision END,
    CASE WHEN jsonb_typeof(analysis->'needs_verification') = 'boolean'
         THEN (analysis->>'needs_verification')::boolean END,
    COALESCE(analyzed_at, now())
FROM reels
WHERE analysis IS NOT NULL AND jsonb_typeof(analysis) = 'object';

INSERT INTO reel_locations (
    reel_code, position, location_name, full_address, locality, district, state,
    country, evidence, confidence, source
)
SELECT
    r.code, a.position::int - 1,
    a.item->>'location_name', a.item->>'full_address', a.item->>'locality',
    a.item->>'district', a.item->>'state', a.item->>'country', a.item->>'evidence',
    CASE WHEN jsonb_typeof(a.item->'confidence') = 'number'
         THEN (a.item->>'confidence')::double precision END,
    a.item->>'source'
FROM reels r,
     jsonb_array_elements(
         CASE WHEN jsonb_typeof(r.analysis->'addresses') = 'array'
              THEN r.analysis->'addresses' ELSE '[]'::jsonb END
     ) WITH ORDINALITY AS a(item, position)
WHERE r.analysis IS NOT NULL AND jsonb_typeof(a.item) = 'object';

ALTER TABLE reels DROP COLUMN analysis, DROP COLUMN analyzed_at;
