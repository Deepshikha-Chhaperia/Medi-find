-- MediFind PostgreSQL Schema (Neon + pgvector)
-- Run once against your Neon database.
-- Enable pgvector extension first (Neon has it pre-installed).

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Documents ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    doc_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_file     TEXT NOT NULL,
    file_type       TEXT,
    file_size_kb    REAL,
    raw_text        TEXT,
    page_count      INTEGER,
    extraction_confidence REAL DEFAULT 0.0,
    status          TEXT DEFAULT 'PENDING',
    -- status: PENDING | EXTRACTED | FAILED | CHUNKED |
    --         ENTITIES_EXTRACTED | NORMALIZED | INDEXED | GEOCODED | COMPLETE
    uploaded_at     TIMESTAMPTZ DEFAULT NOW(),
    processed_at    TIMESTAMPTZ,
    error_message   TEXT
);

-- ─── Chunks + Embeddings (replaces ChromaDB) ─────────────────────────────────
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doc_id          UUID REFERENCES documents(doc_id) ON DELETE CASCADE,
    facility_id     UUID,
    chunk_text      TEXT NOT NULL,
    chunk_index     INTEGER,
    page_number     INTEGER,
    token_count     INTEGER,
    -- pgvector: 384-dim embeddings from all-MiniLM-L6-v2
    embedding       VECTOR(384),
    -- Denormalised metadata for fast filtered search
    facility_name   TEXT,
    state           TEXT,
    district        TEXT,
    facility_type   TEXT,
    emergency_24x7  BOOLEAN,
    capabilities    TEXT[],
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- IVFFlat index for approximate nearest-neighbour search (cosine distance)
CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS chunks_state_idx ON chunks(state);
CREATE INDEX IF NOT EXISTS chunks_district_idx ON chunks(district);
CREATE INDEX IF NOT EXISTS chunks_facility_idx ON chunks(facility_id);

-- ─── Facilities ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS facilities (
    facility_id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    geocoded                BOOLEAN DEFAULT FALSE,
    contact_phone           TEXT,
    contact_email           TEXT,
    website                 TEXT,
    emergency_24x7          BOOLEAN,
    total_beds              INTEGER,
    icu_beds                INTEGER,
    nicu_beds               INTEGER,
    accreditations          TEXT[],
    operational_hours       TEXT,
    source_doc_id           UUID REFERENCES documents(doc_id),
    source_excerpt          TEXT,
    extraction_confidence   REAL DEFAULT 0.0,
    trust_score             REAL DEFAULT 1.0,
    trust_flags             JSONB,
    data_age_days           INTEGER DEFAULT 0,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS facilities_state_idx ON facilities(state);
CREATE INDEX IF NOT EXISTS facilities_district_idx ON facilities(district);
CREATE INDEX IF NOT EXISTS facilities_type_idx ON facilities(facility_type);
CREATE INDEX IF NOT EXISTS facilities_emergency_idx ON facilities(emergency_24x7);

-- ─── Capabilities ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS facility_capabilities (
    id              SERIAL PRIMARY KEY,
    facility_id     UUID REFERENCES facilities(facility_id) ON DELETE CASCADE,
    capability_id   TEXT NOT NULL,
    capability_name TEXT NOT NULL,
    raw_extracted_text TEXT,
    confidence      REAL DEFAULT 0.5,
    source_chunk_id UUID REFERENCES chunks(chunk_id),
    UNIQUE(facility_id, capability_id)
);

CREATE INDEX IF NOT EXISTS cap_facility_idx ON facility_capabilities(facility_id);
CREATE INDEX IF NOT EXISTS cap_id_idx ON facility_capabilities(capability_id);

-- ─── Equipment ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS facility_equipment (
    id              SERIAL PRIMARY KEY,
    facility_id     UUID REFERENCES facilities(facility_id) ON DELETE CASCADE,
    equipment_name  TEXT,
    equipment_canonical TEXT,
    quantity        INTEGER,
    source_chunk_id UUID
);

-- ─── Search Logs ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS search_queries (
    query_id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    raw_query           TEXT,
    structured_query    JSONB,
    result_count        INTEGER,
    top_result_id       UUID,
    processing_time_ms  INTEGER,
    user_lat            REAL,
    user_lng            REAL,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Ingestion Jobs ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    job_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    total_files     INTEGER DEFAULT 0,
    processed_files INTEGER DEFAULT 0,
    failed_files    INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'RUNNING',
    -- status: RUNNING | COMPLETE | FAILED
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

-- ─── Ingestion Source Provenance ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ingestion_sources (
    id              SERIAL PRIMARY KEY,
    job_id          UUID REFERENCES ingestion_jobs(job_id) ON DELETE SET NULL,
    source_type     TEXT NOT NULL, -- google_sheet | file_upload | directory
    source_url      TEXT,
    gid             TEXT,
    csv_url         TEXT,
    rows_fetched    INTEGER DEFAULT 0,
    rows_inserted   INTEGER DEFAULT 0,
    rows_failed     INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'RUNNING', -- RUNNING | COMPLETE | FAILED
    message         TEXT,
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ingestion_sources_job_idx ON ingestion_sources(job_id);
CREATE INDEX IF NOT EXISTS ingestion_sources_started_idx ON ingestion_sources(started_at DESC);

-- ─── Geocoding Cache ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS geocode_cache (
    address_key TEXT PRIMARY KEY,
    lat         REAL,
    lng         REAL,
    cached_at   TIMESTAMPTZ DEFAULT NOW()
);
