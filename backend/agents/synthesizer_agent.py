"""
Agent 8: Synthesizer
Uses Groq to produce a structured, compassionate final answer from retrieved facility context.
"""
from __future__ import annotations
from utils.groq_client import call_groq_json

SYNTHESIS_PROMPT = """You are a compassionate healthcare navigator helping someone find the right medical facility.

User's need: "{query}"

Retrieved facility information (from verified source documents):
{context}

Based ONLY on the information above, produce a helpful structured response.

Return ONLY valid JSON:
{{
  "answer_summary": "2-3 sentence plain English summary of what was found",
  "top_recommendation": {{
    "facility_name": "name of the best match",
    "reason": "specific reason based on source documents why this is best (mention beds, specialties, NABH etc)",
    "important_note": "any critical caveat — e.g. requires referral, OPD only, call ahead"
  }},
  "data_gaps": "mention any missing capability or coverage gap, or null if none",
  "confidence_note": "note if data is older than 6 months, or null",
  "disclaimer": "Always call ahead to confirm current availability before traveling."
}}

Rules:
- Only use information from the retrieved context
- Be specific: mention bed counts, accreditations, hours if available
- Be honest about uncertainty
- Do NOT hallucinate capabilities not mentioned"""


def synthesize(query: str, ranked_chunks: list[dict]) -> dict:
    """
    Produce a structured synthesis from the top-ranked retrieval results.
    Returns a dict with answer_summary, top_recommendation, data_gaps, etc.
    """
    if not ranked_chunks:
        return {
            "answer_summary": "No matching facilities found in the database.",
            "top_recommendation": None,
            "data_gaps": "No facilities in the database match this query.",
            "confidence_note": None,
            "disclaimer": "Always call ahead to confirm current availability before traveling.",
        }

    # Build context from top chunks
    context_parts = []
    seen_facilities = set()
    for chunk in ranked_chunks[:8]:
        fname = chunk.get("facility_name", "Unknown")
        if fname and fname not in seen_facilities:
            seen_facilities.add(fname)
            context_parts.append(
                f"[{fname} — {chunk.get('state', '')}]\n{chunk.get('chunk_text', '')[:600]}"
            )

    context = "\n\n---\n\n".join(context_parts)
    prompt = SYNTHESIS_PROMPT.format(query=query, context=context)
    result = call_groq_json(prompt, max_tokens=600)

    return result or {
        "answer_summary": "Found relevant facilities. Please review the results below.",
        "top_recommendation": None,
        "data_gaps": None,
        "confidence_note": None,
        "disclaimer": "Always call ahead to confirm current availability before traveling.",
    }
