# MediFind: Agentic Healthcare Intelligence System

MediFind is an AI-powered healthcare facility discovery platform that ingests messy healthcare data, extracts capabilities, and returns ranked, explainable results for urgent care search.

## Why This Project Matters

In emergency situations, people lose time figuring out which facility can actually handle a specific case. MediFind converts fragmented source data into actionable facility intelligence so users can find relevant care faster.

## What Makes MediFind Different

- Natural language healthcare search with structured reasoning output.
- Capability normalization for inconsistent medical terminology.
- Trust scoring with contradiction flags.
- Explainable search trace in the UI.
- Source provenance tracking for ingestion audits.
- Map-first exploration with treatment filters and confidence markers.

## Live Architecture Snapshot

- Frontend: React + Vite + TypeScript + Tailwind + Zustand + Leaflet
- Backend: FastAPI (Python)
- Primary data source: public Google Sheet tab
- Optional advanced backend mode: PostgreSQL (Neon) + pgvector
- LLM: Groq (Llama 3.3 70B)
- Retrieval stack: lightweight public-data mode by default, optional agentic backend pipeline

## Deployment Modes

### 1. Simple mode

- Recommended if you want this working quickly on Vercel.
- The app loads facility data from the configured public Google Sheet tab through a lightweight FastAPI endpoint.
- Search, filtering, map views, insights, and admin refresh work without Neon.
- This is the default deployment path.
- Set `VITE_USE_BACKEND=false`.

### 2. Full backend mode

- Use this only if you want PostgreSQL indexing, ingestion jobs, provenance tables, and the full FastAPI search stack.
- Requires `NEON_DATABASE_URL` and the other backend env vars.
- Set `VITE_USE_BACKEND=true`.

## Product Features

- Search flow:
   - natural language query input
   - location-aware radius and sorting
   - confidence labels
   - capability and trust context


- Results and map flow:
   - split list and map UI
   - treatment (capability) filtering
   - 24/7 and facility-type filtering
   - directions and contact shortcuts


- Facility intelligence flow:
   - detailed profile with capabilities
   - source excerpt
   - trust score and flags
   - equipment and metadata coverage


- Admin and ingestion flow:
   - file upload ingestion
   - Google Sheet ingestion trigger
   - ingestion job progress
   - source provenance panel (rows fetched/inserted/failed)

## Configured Source Dataset

Configured Google Sheet tab:

https://docs.google.com/spreadsheets/d/1ZDuDmoQlyxZIEahDBlrMjf2wiWG7xU81/edit?gid=1028775758#gid=1028775758

### Agentic Retrieval-Augmented Generation (RAG)
MediFind doesn't just "keyword match." It uses a multi-agent pipeline:
1. **Query Decomposer**: Interprets medical intent (e.g., "cath lab" → "cardiac emergency").
2. **Hybrid Retrieval**: Semantic search across 10,000+ chunks in a **local SQLite** store with manual vector similarity.
3. **IDP Verification (New)**: Live Groq call verifies top results against query nuance.
4. **Self-Correction (New)**: Trust Scorer re-examines raw notes to clear false alarms.
5. **Synthesizer**: Generates a compassion-first response.

## Quick Start (Local)

1. **Clone & Install**:
   ```bash
   npm install
   pip install -r backend/requirements.txt
   ```

2. **Environment**:
   Copy `.env.example` to `.env`. Only `GROQ_API_KEY` is required. Database is zero-config (SQLite).

This single configured tab is the primary data source in the current deployment model and contains the large hackathon dataset. The backend converts the edit URL into a CSV export URL and reads the configured tab directly.

## Local Setup

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Optional (full local ML retrieval/reranking):

```bash
pip install -r requirements-ml.txt
```

### 2. Frontend

```bash
npm install
npm run dev
```

Frontend env:

- VITE_API_URL=http://localhost:8000
- VITE_USE_BACKEND=false for the simpler Google Sheet mode
- VITE_USE_BACKEND=true only when the full backend is configured
- VITE_GOOGLE_SHEET_URL and VITE_GOOGLE_SHEET_GID are optional overrides for the public sheet source

## Ingestion Commands

### Script ingestion (Google Sheet)

```bash
python scripts/hackathon_ingest.py
```

Optional:

```bash
python scripts/hackathon_ingest.py --limit 500
python scripts/hackathon_ingest.py --sheet-url "<sheet-url>" --gid 1028775758
```
