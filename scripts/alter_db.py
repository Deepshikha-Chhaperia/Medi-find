"""Quick script to add trust_score and trust_flags to existing Neon DB."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent / "backend"))

from db.database import engine

def alter_schema():
    print("Connecting to Neon DB...")
    with engine.connect() as conn:
        try:
            print("Altering facilities table...")
            conn.execute("ALTER TABLE facilities ADD COLUMN IF NOT EXISTS trust_score REAL DEFAULT 1.0;")
            conn.execute("ALTER TABLE facilities ADD COLUMN IF NOT EXISTS trust_flags JSONB;")
            print("Successfully added trust columns!")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    alter_schema()
