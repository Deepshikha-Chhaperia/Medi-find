"""
Agent 4: Capability Normalizer
Maps raw extracted terms to canonical capability IDs using fuzzy matching.
Falls back to LLM for ambiguous terms.
"""
from __future__ import annotations
import json
import os
from rapidfuzz import fuzz, process

_ontology: dict | None = None


def _load_ontology() -> dict:
    global _ontology
    if _ontology is None:
        path = os.path.join(os.path.dirname(__file__), "..", "data", "capability_ontology.json")
        with open(os.path.normpath(path), "r", encoding="utf-8") as f:
            _ontology = json.load(f)
    return _ontology


def normalize_capabilities(raw_terms: list[str]) -> list[dict]:
    """
    Map a list of raw extracted terms to canonical capability IDs.
    Returns list of {capability_id, capability_name, raw_extracted_text, confidence}.
    """
    ontology = _load_ontology()
    results: list[dict] = []
    seen: set[str] = set()

    # Build flat alias → canonical mapping
    alias_map: dict[str, tuple[str, str]] = {}  # alias_lower → (cap_id, cap_label)
    for cap_id, meta in ontology.items():
        label = meta["label"]
        alias_map[label.lower()] = (cap_id, label)
        for alias in meta.get("aliases", []):
            alias_map[alias.lower()] = (cap_id, label)

    all_aliases = list(alias_map.keys())

    for raw in raw_terms:
        if not raw or not raw.strip():
            continue
        raw_lower = raw.lower().strip()

        # Exact match first
        if raw_lower in alias_map:
            cap_id, cap_label = alias_map[raw_lower]
            if cap_id not in seen:
                seen.add(cap_id)
                results.append({
                    "capability_id": cap_id,
                    "capability_name": cap_label,
                    "raw_extracted_text": raw,
                    "confidence": 0.95,
                })
            continue

        # Fuzzy match
        match = process.extractOne(raw_lower, all_aliases, scorer=fuzz.token_sort_ratio)
        if match and match[1] >= 75:
            cap_id, cap_label = alias_map[match[0]]
            if cap_id not in seen:
                seen.add(cap_id)
                results.append({
                    "capability_id": cap_id,
                    "capability_name": cap_label,
                    "raw_extracted_text": raw,
                    "confidence": round(match[1] / 100, 2),
                })

    return results


def extract_capability_ids(raw_terms: list[str]) -> list[str]:
    """Convenience: return just the list of canonical capability IDs."""
    return [c["capability_id"] for c in normalize_capabilities(raw_terms)]
