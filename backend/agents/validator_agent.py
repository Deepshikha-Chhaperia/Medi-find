"""Validator Agent for generating Trust Scores logic."""
from typing import Dict, Any, List
from utils.groq_client import call_groq_json

CORRECTION_PROMPT = """You are a healthcare data auditor. A rule-based system flagged a facility report for potential data inconsistencies.
Your job is to read the RAW TEXT and decide if the flag is a "True Positive" (actually a problem) or a "False Positive" (the information is actually there, but the rules missed it).

Facility: {facility_name}
Flags raised:
{flags_text}

RAW TEXT FROM REPORT:
---
{raw_text}
---

Return ONLY valid JSON:
{{
  "verifications": [
    {{
      "flag": "the text of the flag",
      "is_valid": true/false,
      "reasoning": "brief explanation why"
    }}
  ],
  "corrected_score_adjustment": 0.05,
  "final_trust_note": "summary of auditor findings"
}}

Rules:
- If the raw text explicitly mentions the missing item, set is_valid to false.
- Be conservative. Only clear flags if the text is unambiguous."""

def calculate_trust_score(extracted_data: Dict[str, Any]) -> tuple[float, List[str]]:
    """
    Evaluates extracted unstructured data for contradictions or gaps, yielding a trust score.
    Returns: (trust_score, list_of_flag_reasons)
    """
    score = 1.0
    flags = []

    capabilities = extracted_data.get("capabilities", [])
    equipment = extracted_data.get("equipment", [])
    accreditations = extracted_data.get("accreditations", [])

    # Rule 1: High-risk capability claimed but lacking corresponding equipment/infrastructure
    surgical_caps = {"robotic_surgery", "cardiac_surgery", "neurosurgery", "transplant_kidney", "transplant_liver", "bariatric_surgery", "surgical_oncology", "c_section_24x7"}
    has_surgery = any(c in surgical_caps for c in capabilities)
    
    if has_surgery and not equipment:
        score -= 0.2
        flags.append("Claims surgical capabilities but no specialized equipment (OT, robotic systems, etc) listed in extracted entities.")

    # Rule 2: Claims 24/7 Emergency but no ICU or Blood bank
    is_24x7 = extracted_data.get("emergency_24x7", False)
    has_icu = any("icu" in str(c).lower() for c in capabilities)
    has_blood = "blood_bank" in capabilities

    if is_24x7 and not (has_icu or has_blood):
        score -= 0.15
        flags.append("Claims 24/7 Emergency but lacks ICU or Blood Bank in extracted capabilities.")

    # Rule 3: Very high total beds but no accreditations
    total_beds = extracted_data.get("total_beds", 0) or 0
    if total_beds > 500 and not accreditations:
        score -= 0.1
        flags.append(f"Unusually high bed count ({total_beds}) with no NABH/JCI accreditations found.")

    if score < 0.0:
        score = 0.0

    return score, flags

class ValidatorAgent:
    def __init__(self):
        pass
        
    def self_correct(self, facility_name: str, raw_text: str, current_flags: List[str], current_score: float) -> tuple[float, List[str]]:
        """Use LLM to verify if rule-based flags are indeed correct based on raw text."""
        if not current_flags or not raw_text:
            return current_score, current_flags

        prompt = CORRECTION_PROMPT.format(
            facility_name=facility_name,
            flags_text="\n".join([f"- {f}" for f in current_flags]),
            raw_text=raw_text[:4000] # Truncate for safety
        )
        
        result = call_groq_json(prompt, max_tokens=1000)
        if not result:
            return current_score, current_flags

        new_flags = []
        point_recovery = 0.0
        
        verifications = result.get("verifications", [])
        for v in verifications:
            if v.get("is_valid") is True:
                new_flags.append(v.get("flag"))
            else:
                # Recover points for false positives
                # (Heuristic: 0.1 per cleared flag)
                point_recovery += 0.1

        new_score = min(1.0, current_score + point_recovery)
        
        if point_recovery > 0:
            new_flags.append(f"Self-correction: LLM cleared {len(current_flags) - len(new_flags)} flags after reviewing raw text.")
            
        return round(new_score, 2), new_flags

    def run(self, extracted_facility_data: Dict[str, Any], raw_text: str | None = None) -> Dict[str, Any]:
        """
        Takes the extracted dictionary and attaches trust_score and trust_flags.
        If raw_text is provided, performs an agentic self-correction pass.
        """
        score, flags = calculate_trust_score(extracted_facility_data)
        
        if flags and raw_text:
            score, flags = self_correct(
                extracted_facility_data.get("facility_name", "Unknown"),
                raw_text,
                flags,
                score
            )

        extracted_facility_data["trust_score"] = round(score, 2)
        extracted_facility_data["trust_flags"] = flags
        return extracted_facility_data
