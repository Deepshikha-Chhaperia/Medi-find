-- MediFind SQLite Schema (Local fallback)
-- Replaces PostgreSQL + pgvector for zero-setup local development.

-- ─── Documents ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    doc_id          TEXT PRIMARY KEY,
    source_file     TEXT NOT NULL,
    file_type       TEXT,
    file_size_kb    REAL,
    raw_text        TEXT,
    page_count      INTEGER,
    extraction_confidence REAL DEFAULT 0.0,
    status          TEXT DEFAULT 'PENDING',
    uploaded_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    processed_at    DATETIME,
    error_message   TEXT
);

-- ─── Chunks + Embeddings ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id        TEXT PRIMARY KEY,
    doc_id          TEXT REFERENCES documents(doc_id) ON DELETE CASCADE,
    facility_id     TEXT,
    chunk_text      TEXT NOT NULL,
    chunk_index     INTEGER,
    page_number     INTEGER,
    token_count     INTEGER,
    -- Store vector as JSON or BLOB. We'll use JSON for simplicity in SQLite.
    embedding       TEXT,
    facility_name   TEXT,
    state           TEXT,
    district        TEXT,
    facility_type   TEXT,
    emergency_24x7  BOOLEAN,
    -- Store as JSON string
    capabilities    TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS chunks_state_idx ON chunks(state);
CREATE INDEX IF NOT EXISTS chunks_district_idx ON chunks(district);
CREATE INDEX IF NOT EXISTS chunks_facility_idx ON chunks(facility_id);

-- ─── Facilities ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS facilities (
    facility_id             TEXT PRIMARY KEY,
    facility_name           TEXT NOT NULL,
    facility_name_normalized TEXT,
    facility_type           TEXT,
    address                 TEXT,
    pin_code                TEXT,
    state                   TEXT,
    district                TEXT,
    city                    TEXT,
    lat                     REAL,
    lng                     REAL,
    geocoded                BOOLEAN DEFAULT 0,
    contact_phone           TEXT,
    contact_email           TEXT,
    website                 TEXT,
    emergency_24x7          BOOLEAN,
    total_beds              INTEGER,
    icu_beds                INTEGER,
    nicu_beds               INTEGER,
    -- Store as JSON string
    accreditations          TEXT,
    operational_hours       TEXT,
    source_doc_id           TEXT REFERENCES documents(doc_id),
    source_excerpt          TEXT,
    extraction_confidence   REAL DEFAULT 0.0,
    trust_score             REAL DEFAULT 1.0,
    -- Store as JSON string
    trust_flags             TEXT,
    data_age_days           INTEGER DEFAULT 0,
    created_at              DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS facilities_state_idx ON facilities(state);
CREATE INDEX IF NOT EXISTS facilities_district_idx ON facilities(district);

-- ─── Capabilities ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS facility_capabilities (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id     TEXT REFERENCES facilities(facility_id) ON DELETE CASCADE,
    capability_id   TEXT NOT NULL,
    capability_name TEXT NOT NULL,
    raw_extracted_text TEXT,
    confidence      REAL DEFAULT 0.5,
    source_chunk_id TEXT REFERENCES chunks(chunk_id),
    UNIQUE(facility_id, capability_id)
);

-- ─── Equipment ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS facility_equipment (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id     TEXT REFERENCES facilities(facility_id) ON DELETE CASCADE,
    equipment_name  TEXT,
    equipment_canonical TEXT,
    quantity        INTEGER,
    source_chunk_id TEXT
);

-- ─── Search Logs ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS search_queries (
    query_id            TEXT PRIMARY KEY,
    raw_query           TEXT,
    structured_query    TEXT,
    result_count        INTEGER,
    top_result_id       TEXT,
    processing_time_ms  INTEGER,
    user_lat            REAL,
    user_lng            REAL,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ─── Ingestion Jobs ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    job_id          TEXT PRIMARY KEY,
    total_files     INTEGER DEFAULT 0,
    processed_files INTEGER DEFAULT 0,
    failed_files    INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'RUNNING',
    started_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at    DATETIME
);

-- ─── Ingestion Source Provenance ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ingestion_sources (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id          TEXT REFERENCES ingestion_jobs(job_id) ON DELETE SET NULL,
    source_type     TEXT NOT NULL,
    source_url      TEXT,
    gid             TEXT,
    csv_url         TEXT,
    rows_fetched    INTEGER DEFAULT 0,
    rows_inserted   INTEGER DEFAULT 0,
    rows_failed     INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'RUNNING',
    message         TEXT,
    started_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at    DATETIME
);

-- ─── Geocoding Cache ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS geocode_cache (
    address_key TEXT PRIMARY KEY,
    lat         REAL,
    lng         REAL,
    cached_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);
