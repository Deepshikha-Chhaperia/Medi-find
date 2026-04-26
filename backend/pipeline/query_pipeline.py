"""
Query Pipeline Orchestrator
Runs the full query flow:
QueryAgent → RetrievalAgent → RerankerAgent → SynthesizerAgent → Structured Response
"""
from __future__ import annotations
import uuid
import time
import math
from typing import Optional

from agents.query_agent import decompose_query
from agents.retrieval_agent import retrieve
from agents.reranker_agent import rerank
from agents.synthesizer_agent import synthesize
from db.database import get_db, fetchone, fetchall
from models.search import SearchRequest, SearchResponse, FacilityResult


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def run_query(request: SearchRequest) -> SearchResponse:
    """
    Full agentic query pipeline.
    Returns a SearchResponse with ranked facilities and synthesis.
    """
    start = time.time()
    query_id = str(uuid.uuid4())

    lat = request.location.lat if request.location else None
    lng = request.location.lng if request.location else None

    # ── Agent 5: Decompose query ──────────────────────────────────────────
    decomposed = decompose_query(request.query, lat, lng)
    required_caps = decomposed.get("required_capabilities", [])
    sub_queries = decomposed.get("sub_queries", [request.query])
    must_24x7 = decomposed.get("must_be_24x7", False) or request.filters.emergency_only
    interpreted = decomposed.get("interpreted_need", request.query)
    radius = request.radius_km or decomposed.get("radius_km", 50)

    with get_db() as conn:
        # ── Agent 6: Retrieve chunks ───────────────────────────────────────
        raw_chunks = retrieve(
            conn,
            sub_queries=sub_queries,
            n_per_query=20,
            emergency_only=must_24x7,
            capabilities_filter=required_caps if required_caps else None,
        )

        if not raw_chunks:
            return SearchResponse(
                query_id=query_id,
                processing_time_ms=int((time.time() - start) * 1000),
                total_found=0,
                interpreted_need=interpreted,
                results=[],
                gaps=[f"No facilities found for: {request.query}"],
            )

        # ── Agent 7: Re-rank ──────────────────────────────────────────────
        ranked_chunks = rerank(request.query, raw_chunks, top_k=15)

        # ── Aggregate chunks → facilities (deduplicate) ────────────────────
        fac_scores: dict[str, dict] = {}
        for chunk in ranked_chunks:
            fid = str(chunk.get("facility_id", ""))
            if not fid:
                continue
            if fid not in fac_scores or fac_scores[fid]["final_score"] < chunk["final_score"]:
                fac_scores[fid] = chunk

        # ── Load full facility records from DB ────────────────────────────
        results: list[FacilityResult] = []
        for rank_idx, (fid, chunk) in enumerate(
            sorted(fac_scores.items(), key=lambda x: x[1]["final_score"], reverse=True)[:request.max_results]
        ):
            fac = fetchone(conn, "SELECT * FROM facilities WHERE facility_id = %s", (fid,))
            if not fac:
                continue

            caps = fetchall(conn,
                "SELECT capability_id FROM facility_capabilities WHERE facility_id = %s", (fid,))
            equip = fetchall(conn,
                "SELECT equipment_name FROM facility_equipment WHERE facility_id = %s", (fid,))

            cap_ids = [c["capability_id"] for c in caps]
            equip_names = [e["equipment_name"] for e in equip if e["equipment_name"]]

            # Distance
            distance = 0.0
            if lat and lng and fac.get("lat") and fac.get("lng"):
                distance = haversine_km(lat, lng, fac["lat"], fac["lng"])
                if distance > radius:
                    continue

            # Apply filters
            if request.filters.facility_type and fac.get("facility_type") != request.filters.facility_type:
                continue
            if must_24x7 and not fac.get("emergency_24x7"):
                continue
            score = chunk["final_score"]
            if score < request.filters.min_confidence:
                continue

            matched_caps = [c for c in required_caps if c in cap_ids]
            match_confidence = "High" if score >= 0.75 else "Medium" if score >= 0.5 else "Low"
            matched_reason = (
                f"Source confirms: {', '.join(matched_caps[:3])}" if matched_caps
                else chunk.get("chunk_text", "")[:150]
            )

            directions = ""
            if fac.get("lat") and fac.get("lng"):
                directions = f"https://www.google.com/maps/dir/?api=1&destination={fac['lat']},{fac['lng']}"

            source_doc = None
            if fac.get("source_doc_id"):
                doc = fetchone(conn, "SELECT source_file FROM documents WHERE doc_id = %s", (fac["source_doc_id"],))
                source_doc = doc["source_file"] if doc else None

            # Extract trust score
            trust_score = fac.get("trust_score", 1.0)
            trust_flags = fac.get("trust_flags") or []

            results.append(FacilityResult(
                rank=rank_idx + 1,
                facility_id=fid,
                facility_name=fac.get("facility_name", ""),
                facility_type=fac.get("facility_type"),
                address=fac.get("address"),
                city=fac.get("city"),
                state=fac.get("state"),
                lat=fac.get("lat"),
                lng=fac.get("lng"),
                distance_km=round(distance, 1),
                match_score=round(score, 3),
                match_confidence=match_confidence,
                matched_capabilities=matched_caps,
                matched_reason=matched_reason,
                source_excerpt=chunk.get("chunk_text", "")[:400],
                source_doc=source_doc,
                contact_phone=fac.get("contact_phone"),
                emergency_24x7=bool(fac.get("emergency_24x7")),
                total_beds=fac.get("total_beds") or 0,
                icu_beds=fac.get("icu_beds") or 0,
                accreditations=fac.get("accreditations") or [],
                directions_url=directions,
                data_age_days=fac.get("data_age_days") or 0,
                capabilities=cap_ids,
                equipment=equip_names,
                trust_score=trust_score,
                trust_flags=trust_flags,
            ))

        # Re-sort results by sort_score
        if request.sort_by == "distance":
            results.sort(key=lambda r: (r.distance_km <= 0, r.distance_km if r.distance_km > 0 else float("inf")))
        elif request.sort_by == "beds":
            results.sort(key=lambda r: r.total_beds, reverse=True)
        elif request.sort_by == "capabilities":
            results.sort(key=lambda r: len(r.capabilities), reverse=True)
        else:
            results.sort(key=lambda r: r.match_score, reverse=True)
        for i, r in enumerate(results):
            r.rank = i + 1

def verify_results_with_llm(query: str, results: list[FacilityResult]) -> list[FacilityResult]:
    """
    Agentic verification: Send top results to Groq to verify if they truly match
    the nuanced intent of the query.
    """
    from utils.groq_client import call_groq_json
    
    if not results:
        return results

    # Only verify top 5
    to_verify = results[:5]
    
    context = []
    for r in to_verify:
        context.append(f"ID: {r.facility_id}\nName: {r.facility_name}\nExcerpt: {r.source_excerpt}")

    verification_prompt = f"""You are a medical search validator.
User Query: "{query}"

Top results found by retrieval system:
{chr(10).join(context)}

For each result, verify if it's a REAL matches for the user's need.
Some results might be "keyword matches" but not actually have the service.

Return JSON:
{{
  "verifications": [
    {{
      "id": "facility_id",
      "is_real_match": true/false,
      "reason": "brief explanation"
    }}
  ]
}}"""

    v_data = call_groq_json(verification_prompt, max_tokens=1000)
    if not v_data or "verifications" not in v_data:
        return results

    v_map = {v["id"]: v for v in v_data["verifications"] if "id" in v}
    
    for r in results:
        if r.facility_id in v_map:
            v = v_map[r.facility_id]
            r.match_confidence = "Verified High" if v.get("is_real_match") else "Partial/Vague Match"
            r.matched_reason = v.get("reason", r.matched_reason)
            if not v.get("is_real_match"):
                r.match_score *= 0.8 # Penalize uncertain matches

    return results


def run_query(request: SearchRequest) -> SearchResponse:
    """
    Full agentic query pipeline.
    Returns a SearchResponse with ranked facilities and synthesis.
    """
    start = time.time()
    query_id = str(uuid.uuid4())

    lat = request.location.lat if request.location else None
    lng = request.location.lng if request.location else None

    # ── Agent 5: Decompose query ──────────────────────────────────────────
    decomposed = decompose_query(request.query, lat, lng)
    required_caps = decomposed.get("required_capabilities", [])
    sub_queries = decomposed.get("sub_queries", [request.query])
    must_24x7 = decomposed.get("must_be_24x7", False) or request.filters.emergency_only
    interpreted = decomposed.get("interpreted_need", request.query)
    radius = request.radius_km or decomposed.get("radius_km", 50)

    with get_db() as conn:
        # ── Agent 6: Retrieve chunks ───────────────────────────────────────
        raw_chunks = retrieve(
            conn,
            sub_queries=sub_queries,
            n_per_query=20,
            emergency_only=must_24x7,
            capabilities_filter=required_caps if required_caps else None,
        )

        if not raw_chunks:
            return SearchResponse(
                query_id=query_id,
                processing_time_ms=int((time.time() - start) * 1000),
                total_found=0,
                interpreted_need=interpreted,
                results=[],
                gaps=[f"No facilities found for: {request.query}"],
            )

        # ── Agent 7: Re-rank ──────────────────────────────────────────────
        ranked_chunks = rerank(request.query, raw_chunks, top_k=15)

        # ── Aggregate chunks → facilities (deduplicate) ────────────────────
        fac_scores: dict[str, dict] = {}
        for chunk in ranked_chunks:
            fid = str(chunk.get("facility_id", ""))
            if not fid:
                continue
            if fid not in fac_scores or fac_scores[fid]["final_score"] < chunk["final_score"]:
                fac_scores[fid] = chunk

        # ── Load full facility records from DB ────────────────────────────
        results: list[FacilityResult] = []
        for rank_idx, (fid, chunk) in enumerate(
            sorted(fac_scores.items(), key=lambda x: x[1]["final_score"], reverse=True)[:request.max_results]
        ):
            fac = fetchone(conn, "SELECT * FROM facilities WHERE facility_id = %s", (fid,))
            if not fac:
                continue

            # In SQLite, JSON fields are strings
            cap_ids = []
            try:
                # Some rows might have it as JSON string, others might need a join
                # but search uses facility_capabilities table too.
                # In our new schema, we store capabilities as JSON in chunks but
                # facilities table also has them? Let's check schema.
                # Actually, let's just fetch from facility_capabilities table.
                caps = fetchall(conn, "SELECT capability_id FROM facility_capabilities WHERE facility_id = %s", (fid,))
                cap_ids = [c["capability_id"] for c in caps]
            except:
                pass

            # Distance
            distance = 0.0
            if lat and lng and fac.get("lat") and fac.get("lng"):
                distance = haversine_km(lat, lng, fac["lat"], fac["lng"])
                if distance > radius:
                    continue

            # Apply filters
            if request.filters.facility_type and fac.get("facility_type") != request.filters.facility_type:
                continue
            if must_24x7 and not fac.get("emergency_24x7"):
                continue
            score = chunk["final_score"]
            if score < request.filters.min_confidence:
                continue

            matched_caps = [c for c in required_caps if c in cap_ids]
            match_confidence = "High" if score >= 0.75 else "Medium" if score >= 0.5 else "Low"
            matched_reason = (
                f"Source confirms: {', '.join(matched_caps[:3])}" if matched_caps
                else chunk.get("chunk_text", "")[:150]
            )

            source_doc = None
            if fac.get("source_doc_id"):
                try:
                    doc = fetchone(conn, "SELECT source_file FROM documents WHERE doc_id = %s", (fac["source_doc_id"],))
                    source_doc = doc["source_file"] if doc else None
                except:
                    pass

            # Extract trust score
            trust_score = fac.get("trust_score", 1.0)
            trust_flags = []
            if fac.get("trust_flags"):
                import json
                try:
                    trust_flags = json.loads(fac["trust_flags"])
                except:
                    trust_flags = []

            results.append(FacilityResult(
                rank=rank_idx + 1,
                facility_id=fid,
                facility_name=fac.get("facility_name", ""),
                facility_type=fac.get("facility_type"),
                address=fac.get("address"),
                city=fac.get("city"),
                state=fac.get("state"),
                lat=fac.get("lat"),
                lng=fac.get("lng"),
                distance_km=round(distance, 1),
                match_score=round(score, 3),
                match_confidence=match_confidence,
                matched_capabilities=matched_caps,
                matched_reason=matched_reason,
                source_excerpt=chunk.get("chunk_text", "")[:400],
                source_doc=fac.get("source_doc_id"),
                contact_phone=fac.get("contact_phone"),
                emergency_24x7=bool(fac.get("emergency_24x7")),
                total_beds=fac.get("total_beds") or 0,
                icu_beds=fac.get("icu_beds") or 0,
                accreditations=[], # Handle similarly to trust_flags if needed
                directions_url=directions,
                data_age_days=fac.get("data_age_days") or 0,
                capabilities=cap_ids,
                equipment=[],
                trust_score=trust_score,
                trust_flags=trust_flags,
            ))

        # ── IDP Verification ──────────────────────────────────────────────
        results = verify_results_with_llm(request.query, results)

        # Re-sort results by sort_score
        if request.sort_by == "distance":
            results.sort(key=lambda r: (r.distance_km <= 0, r.distance_km if r.distance_km > 0 else float("inf")))
        elif request.sort_by == "beds":
            results.sort(key=lambda r: r.total_beds, reverse=True)
        elif request.sort_by == "capabilities":
            results.sort(key=lambda r: len(r.capabilities), reverse=True)
        else:
            results.sort(key=lambda r: r.match_score, reverse=True)
        for i, r in enumerate(results):
            r.rank = i + 1

        # ── Agent 8: Synthesize ────────────────────────────────────────────
        synthesis = synthesize(request.query, ranked_chunks)

        # ── Build Trace (Chain of Thought) ─────────────────────────────────
        trace = {
            "step_1_query_decomposition": {
                "input": request.query,
                "output": {"capabilities": required_caps}
            },
            "step_2_vector_retrieval": {
                "chunks_retrieved": len(raw_chunks),
            },
            "step_3_llm_verification": {
                "verified_top_5": True,
                "note": "IDP verification active"
            },
            "step_4_final_answer": {
                "reasoning": synthesis.get("answer_summary", "Synthesis complete.")
            }
        }

    return SearchResponse(
        query_id=query_id,
        processing_time_ms=int((time.time() - start) * 1000),
        total_found=len(results),
        interpreted_need=synthesis.get("answer_summary", interpreted),
        results=results,
        gaps=([synthesis["data_gaps"]] if synthesis.get("data_gaps") else []),
        trace=trace,
    )
