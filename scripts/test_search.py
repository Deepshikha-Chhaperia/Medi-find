"""
End-to-end test of the MediFind query pipeline.
Run after ingesting at least a few documents.

Usage: python scripts/test_search.py
"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

from models.search import SearchRequest, LocationIn, SearchFilters
from pipeline.query_pipeline import run_query

TEST_CASES = [
    {"query": "nearest NICU for premature baby in Kolkata", "lat": 22.5726, "lng": 88.3639},
    {"query": "24 hour emergency cardiac cath lab Hyderabad", "lat": 17.3850, "lng": 78.4867},
    {"query": "liver transplant hospital near Bengaluru", "lat": 12.9716, "lng": 77.5946},
    {"query": "burn unit with ICU Lucknow night emergency", "lat": 26.8467, "lng": 80.9462},
    {"query": "dialysis centre accepting new patients Chennai", "lat": 13.0827, "lng": 80.2707},
]

def main():
    print(f"\n{'='*70}")
    print("  MediFind Query Pipeline Test")
    print(f"{'='*70}\n")

    for i, tc in enumerate(TEST_CASES):
        print(f"Test {i+1}: {tc['query']}")
        req = SearchRequest(
            query=tc["query"],
            location=LocationIn(lat=tc["lat"], lng=tc["lng"]),
            radius_km=50,
            filters=SearchFilters(),
            max_results=5,
        )
        try:
            resp = run_query(req)
            print(f"  → {resp.total_found} results in {resp.processing_time_ms}ms")
            print(f"  → Interpreted: {resp.interpreted_need[:80]}")
            for r in resp.results[:3]:
                print(f"  [{r.rank}] {r.facility_name} ({r.state}) — score={r.match_score} dist={r.distance_km}km")
            if resp.gaps:
                print(f"  ⚠ Gaps: {resp.gaps[0]}")
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
        print()

if __name__ == "__main__":
    main()
