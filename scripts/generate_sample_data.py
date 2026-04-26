"""
Generate 50 realistic synthetic hospital facility reports.
These simulate messy, real-world facility documents:
- Varying format quality (some structured, some free-text)
- Terminological inconsistency (same capability, different words)
- Partial information (not every field present)
- Typos and abbreviations

Run: python scripts/generate_sample_data.py
Output: backend/data/raw/*.txt (50 files)
"""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "raw")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─── Facility master list ─────────────────────────────────────────────────────
FACILITIES = [
    # Hyderabad
    {"name": "KIMS Hospital Secunderabad", "city": "Hyderabad", "district": "Secunderabad", "state": "Telangana",
     "address": "1-8-31/1, Minister Road, Secunderabad 500003", "phone": "+91-40-4488-5000",
     "beds": 1000, "icu": 150, "nicu": 25, "emergency": True,
     "caps": ["trauma_center", "stroke_unit", "cardiac_emergency", "icu_general", "icu_cardiac", "icu_neuro",
              "nicu", "picu", "mri", "ct_scan", "pet_ct", "cath_lab", "cardiac_surgery", "neurosurgery",
              "transplant_kidney", "dialysis", "blood_bank", "chemotherapy", "radiation_therapy"],
     "equip": ["3T MRI", "128-slice CT", "PET-CT", "Cath Lab x3", "Linear accelerator"],
     "accr": ["NABH", "JCI"], "hours": "24x7"},
    {"name": "Apollo Hospital Jubilee Hills", "city": "Hyderabad", "district": "Hyderabad", "state": "Telangana",
     "address": "Film Nagar Road, Jubilee Hills, Hyderabad 500033", "phone": "+91-40-2360-7777",
     "beds": 700, "icu": 100, "nicu": 18, "emergency": True,
     "caps": ["trauma_center", "cardiac_emergency", "icu_general", "icu_cardiac", "nicu", "mri", "ct_scan",
              "cath_lab", "robotic_surgery", "cardiac_surgery", "transplant_kidney", "dialysis", "blood_bank",
              "chemotherapy", "radiation_therapy"],
     "equip": ["3T MRI", "da Vinci Xi", "Cath Lab x2", "Linac", "PET-CT"],
     "accr": ["NABH", "JCI"], "hours": "24x7"},
    {"name": "Yashoda Hospital Secunderabad", "city": "Hyderabad", "district": "Secunderabad", "state": "Telangana",
     "address": "Nalgonda X Road, Malakpet, Hyderabad 500036", "phone": "+91-40-4567-4567",
     "beds": 600, "icu": 90, "nicu": 20, "emergency": True,
     "caps": ["cardiac_emergency", "icu_general", "icu_cardiac", "nicu", "mri", "ct_scan", "cath_lab",
              "cardiac_surgery", "dialysis", "blood_bank"],
     "equip": ["MRI", "CT scanner", "Cath Lab x2", "Dialysis x20"],
     "accr": ["NABH"], "hours": "24x7"},
    {"name": "NIMS Hyderabad", "city": "Hyderabad", "district": "Hyderabad", "state": "Telangana",
     "address": "Panjagutta, Hyderabad 500082", "phone": "+91-40-2348-9000",
     "beds": 2500, "icu": 200, "nicu": 40, "emergency": True,
     "caps": ["trauma_center", "stroke_unit", "cardiac_emergency", "icu_general", "icu_cardiac", "icu_neuro",
              "nicu", "picu", "mri", "ct_scan", "pet_ct", "cath_lab", "cardiac_surgery", "neurosurgery",
              "burn_unit", "psychiatric_unit", "dialysis", "blood_bank"],
     "equip": ["MRI", "CT", "Cath Lab", "Burns ward 30 beds"],
     "accr": ["NABH"], "hours": "24x7"},
    # Pune
    {"name": "Ruby Hall Clinic", "city": "Pune", "district": "Pune", "state": "Maharashtra",
     "address": "40 Sassoon Road, Pune 411001", "phone": "+91-20-6645-5000",
     "beds": 450, "icu": 70, "nicu": 12, "emergency": True,
     "caps": ["trauma_center", "cardiac_emergency", "icu_general", "icu_cardiac", "nicu", "mri", "ct_scan",
              "cath_lab", "cardiac_surgery", "neurosurgery", "dialysis", "blood_bank", "chemotherapy"],
     "equip": ["1.5T MRI", "64-slice CT", "Cath Lab x2"],
     "accr": ["NABH", "JCI"], "hours": "24x7"},
    {"name": "Jehangir Hospital", "city": "Pune", "district": "Pune", "state": "Maharashtra",
     "address": "32 Sassoon Road, Pune 411001", "phone": "+91-20-6681-5000",
     "beds": 400, "icu": 60, "nicu": 10, "emergency": True,
     "caps": ["icu_general", "nicu", "cardiac_emergency", "ct_scan", "mri", "blood_bank", "dialysis"],
     "equip": ["MRI", "CT", "Dialysis x15"],
     "accr": ["NABH"], "hours": "24x7"},
    {"name": "Sahyadri Hospitals Pune", "city": "Pune", "district": "Pune", "state": "Maharashtra",
     "address": "30 Karve Road, Pune 411004", "phone": "+91-20-6721-1111",
     "beds": 350, "icu": 55, "nicu": 14, "emergency": True,
     "caps": ["cardiac_emergency", "icu_general", "icu_cardiac", "nicu", "mri", "ct_scan", "cath_lab",
              "cardiac_surgery", "dialysis", "blood_bank"],
     "equip": ["3T MRI", "Cath Lab", "CT scanner"],
     "accr": ["NABH"], "hours": "24x7"},
    {"name": "KEM Hospital Pune", "city": "Pune", "district": "Pune", "state": "Maharashtra",
     "address": "489 Rasta Peth, Pune 411011", "phone": "+91-20-2661-3921",
     "beds": 1800, "icu": 120, "nicu": 30, "emergency": True,
     "caps": ["trauma_center", "icu_general", "nicu", "picu", "ct_scan", "mri", "burn_unit",
              "dialysis", "blood_bank", "psychiatric_unit"],
     "equip": ["CT scanner", "MRI", "Burns unit 25 beds"],
     "accr": ["NABH"], "hours": "24x7"},
    # Jaipur
    {"name": "SMS Medical College Hospital", "city": "Jaipur", "district": "Jaipur", "state": "Rajasthan",
     "address": "JLN Marg, Jaipur 302004", "phone": "+91-141-256-0291",
     "beds": 3500, "icu": 250, "nicu": 50, "emergency": True,
     "caps": ["trauma_center", "stroke_unit", "cardiac_emergency", "icu_general", "icu_neuro", "nicu", "picu",
              "mri", "ct_scan", "cath_lab", "cardiac_surgery", "neurosurgery", "burn_unit", "dialysis",
              "blood_bank", "psychiatric_unit"],
     "equip": ["MRI", "CT", "Cath Lab", "Burns ICU"],
     "accr": ["NABH"], "hours": "24x7"},
    {"name": "Fortis Escorts Hospital Jaipur", "city": "Jaipur", "district": "Jaipur", "state": "Rajasthan",
     "address": "Jawahar Lal Nehru Marg, Malviya Nagar, Jaipur 302017", "phone": "+91-141-254-7000",
     "beds": 350, "icu": 60,  "nicu": 12, "emergency": True,
     "caps": ["cardiac_emergency", "icu_general", "icu_cardiac", "nicu", "mri", "ct_scan", "pet_ct",
              "cath_lab", "cardiac_surgery", "dialysis", "blood_bank", "chemotherapy", "radiation_therapy"],
     "equip": ["3T MRI", "PET-CT", "Cath Lab x2", "Linac"],
     "accr": ["NABH", "JCI"], "hours": "24x7"},
    # Ahmedabad
    {"name": "Sterling Hospitals Ahmedabad", "city": "Ahmedabad", "district": "Ahmedabad", "state": "Gujarat",
     "address": "Off Gurukul Road, Memnagar, Ahmedabad 380052", "phone": "+91-79-4000-4000",
     "beds": 500, "icu": 80, "nicu": 16, "emergency": True,
     "caps": ["cardiac_emergency", "icu_general", "icu_cardiac", "nicu", "mri", "ct_scan", "cath_lab",
              "cardiac_surgery", "neurosurgery", "dialysis", "blood_bank"],
     "equip": ["3T MRI", "Cath Lab x2", "CT"],
     "accr": ["NABH"], "hours": "24x7"},
    {"name": "CIMS Hospital Ahmedabad", "city": "Ahmedabad", "district": "Ahmedabad", "state": "Gujarat",
     "address": "Near Shukan Mall, Off Science City Road, Ahmedabad 380060", "phone": "+91-79-3010-1234",
     "beds": 400, "icu": 65, "nicu": 14, "emergency": True,
     "caps": ["stroke_unit", "cardiac_emergency", "icu_general", "nicu", "mri", "ct_scan", "pet_ct",
              "cath_lab", "robotic_surgery", "cardiac_surgery", "transplant_kidney", "dialysis", "blood_bank",
              "chemotherapy"],
     "equip": ["3T MRI", "PET-CT", "da Vinci", "Cath Lab x3"],
     "accr": ["NABH", "JCI"], "hours": "24x7"},
    # Lucknow
    {"name": "KGMU King George's Medical University", "city": "Lucknow", "district": "Lucknow", "state": "Uttar Pradesh",
     "address": "Shah Mina Rd, Lucknow 226003", "phone": "+91-522-225-7540",
     "beds": 4000, "icu": 300, "nicu": 60, "emergency": True,
     "caps": ["trauma_center", "stroke_unit", "cardiac_emergency", "icu_general", "icu_neuro", "nicu", "picu",
              "mri", "ct_scan", "pet_ct", "cath_lab", "cardiac_surgery", "neurosurgery", "transplant_kidney",
              "burn_unit", "psychiatric_unit", "dialysis", "blood_bank", "chemotherapy", "radiation_therapy"],
     "equip": ["MRI x2", "CT", "PET-CT", "Cath Lab x2", "Linac"],
     "accr": ["NABH"], "hours": "24x7"},
    {"name": "Medanta Hospital Lucknow", "city": "Lucknow", "district": "Lucknow", "state": "Uttar Pradesh",
     "address": "Sector B, Pocket 1, Gomti Nagar Extension, Lucknow 226010", "phone": "+91-522-450-4444",
     "beds": 520, "icu": 90, "nicu": 20, "emergency": True,
     "caps": ["cardiac_emergency", "icu_general", "icu_cardiac", "nicu", "mri", "ct_scan", "pet_ct",
              "cath_lab", "robotic_surgery", "cardiac_surgery", "transplant_kidney", "dialysis", "blood_bank"],
     "equip": ["3T MRI", "PET-CT", "da Vinci", "Cath Lab x3"],
     "accr": ["NABH", "JCI"], "hours": "24x7"},
    # Chandigarh
    {"name": "PGIMER Chandigarh", "city": "Chandigarh", "district": "Chandigarh", "state": "Punjab",
     "address": "Sector 12, Chandigarh 160012", "phone": "+91-172-275-6565",
     "beds": 3000, "icu": 220, "nicu": 45, "emergency": True,
     "caps": ["trauma_center", "stroke_unit", "cardiac_emergency", "icu_general", "icu_cardiac", "icu_neuro",
              "nicu", "picu", "mri", "ct_scan", "pet_ct", "cath_lab", "cardiac_surgery", "neurosurgery",
              "transplant_kidney", "transplant_liver", "burn_unit", "psychiatric_unit", "dialysis",
              "blood_bank", "chemotherapy", "radiation_therapy", "surgical_oncology"],
     "equip": ["3T MRI x2", "PET-CT", "Cath Lab x4", "Linac x3", "Brachytherapy"],
     "accr": ["NABH"], "hours": "24x7"},
    {"name": "Fortis Hospital Mohali", "city": "Mohali", "district": "Mohali", "state": "Punjab",
     "address": "Sector 62, Phase 8, Mohali 160062", "phone": "+91-172-492-2222",
     "beds": 350, "icu": 55, "nicu": 12, "emergency": True,
     "caps": ["cardiac_emergency", "icu_general", "icu_cardiac", "nicu", "mri", "ct_scan", "cath_lab",
              "cardiac_surgery", "neurosurgery", "dialysis", "blood_bank"],
     "equip": ["3T MRI", "Cath Lab x2", "CT"],
     "accr": ["NABH", "JCI"], "hours": "24x7"},
    # Kochi
    {"name": "Amrita Institute of Medical Sciences", "city": "Kochi", "district": "Ernakulam", "state": "Kerala",
     "address": "AIMS Ponekkara, Kochi 682041", "phone": "+91-484-280-1234",
     "beds": 1375, "icu": 160, "nicu": 28, "emergency": True,
     "caps": ["trauma_center", "stroke_unit", "cardiac_emergency", "icu_general", "icu_cardiac", "icu_neuro",
              "nicu", "picu", "mri", "ct_scan", "pet_ct", "cath_lab", "robotic_surgery", "cardiac_surgery",
              "neurosurgery", "transplant_kidney", "transplant_liver", "dialysis", "blood_bank",
              "chemotherapy", "radiation_therapy", "surgical_oncology"],
     "equip": ["3T MRI x2", "PET-CT", "da Vinci", "CyberKnife", "Cath Lab x4"],
     "accr": ["NABH", "JCI", "NABL"], "hours": "24x7"},
    {"name": "Aster Medcity Kochi", "city": "Kochi", "district": "Ernakulam", "state": "Kerala",
     "address": "Kuttisahib Road, South Chittoor, Kochi 682027", "phone": "+91-484-666-8800",
     "beds": 670, "icu": 110, "nicu": 22, "emergency": True,
     "caps": ["cardiac_emergency", "icu_general", "icu_cardiac", "nicu", "mri", "ct_scan", "pet_ct",
              "cath_lab", "robotic_surgery", "cardiac_surgery", "transplant_kidney", "dialysis", "blood_bank",
              "chemotherapy", "radiation_therapy"],
     "equip": ["3T MRI", "PET-CT", "da Vinci", "Cath Lab x3", "Linac"],
     "accr": ["NABH", "JCI"], "hours": "24x7"},
    # More Chennai
    {"name": "MIOT International Hospital", "city": "Chennai", "district": "Chennai", "state": "Tamil Nadu",
     "address": "4/112, Mount Poonamallee Road, Manapakkam, Chennai 600089", "phone": "+91-44-2249-7000",
     "beds": 1000, "icu": 130, "nicu": 20, "emergency": True,
     "caps": ["trauma_center", "cardiac_emergency", "icu_general", "nicu", "mri", "ct_scan", "cath_lab",
              "robotic_surgery", "cardiac_surgery", "neurosurgery", "transplant_kidney", "dialysis", "blood_bank"],
     "equip": ["3T MRI", "Cath Lab x3", "da Vinci", "CT"],
     "accr": ["NABH", "JCI"], "hours": "24x7"},
    {"name": "Sri Ramachandra Medical Centre", "city": "Chennai", "district": "Chennai", "state": "Tamil Nadu",
     "address": "No.1 Ramachandra Nagar, Porur, Chennai 600116", "phone": "+91-44-4592-8600",
     "beds": 1500, "icu": 180, "nicu": 32, "emergency": True,
     "caps": ["trauma_center", "stroke_unit", "cardiac_emergency", "icu_general", "icu_neuro", "nicu", "picu",
              "mri", "ct_scan", "pet_ct", "cath_lab", "cardiac_surgery", "neurosurgery", "transplant_kidney",
              "transplant_liver", "radiation_therapy", "chemotherapy", "dialysis", "blood_bank"],
     "equip": ["3T MRI", "PET-CT", "Cath Lab x3", "Linac x2"],
     "accr": ["NABH", "NABL"], "hours": "24x7"},
    # More Bengaluru
    {"name": "Fortis Hospital Cunningham Road", "city": "Bengaluru", "district": "Bengaluru Urban", "state": "Karnataka",
     "address": "14 Cunningham Road, Bengaluru 560052", "phone": "+91-80-6621-4444",
     "beds": 264, "icu": 45, "nicu": 10, "emergency": True,
     "caps": ["cardiac_emergency", "icu_general", "icu_cardiac", "nicu", "mri", "ct_scan", "cath_lab",
              "cardiac_surgery", "dialysis", "blood_bank"],
     "equip": ["3T MRI", "Cath Lab x2", "CT"],
     "accr": ["NABH", "JCI"], "hours": "24x7"},
    {"name": "St. John's Medical College Hospital", "city": "Bengaluru", "district": "Bengaluru Urban", "state": "Karnataka",
     "address": "Sarjapur Road, Koramangala, Bengaluru 560034", "phone": "+91-80-2206-5000",
     "beds": 1250, "icu": 130, "nicu": 25, "emergency": True,
     "caps": ["trauma_center", "icu_general", "nicu", "picu", "ct_scan", "mri", "cardiac_surgery",
              "neurosurgery", "dialysis", "blood_bank", "burn_unit", "psychiatric_unit"],
     "equip": ["CT", "MRI", "Cath Lab"],
     "accr": ["NABH"], "hours": "24x7"},
    # PHCs / smaller
    {"name": "PHC Jubilee Hills Hyderabad", "city": "Hyderabad", "district": "Hyderabad", "state": "Telangana",
     "address": "Road No. 2, Jubilee Hills, Hyderabad 500033", "phone": "+91-40-2354-1100",
     "beds": 30, "icu": 0, "nicu": 0, "emergency": False,
     "caps": ["pathology_lab", "blood_bank"],
     "equip": ["Basic lab", "ECG machine"],
     "accr": [], "hours": "OPD 9am-5pm Mon-Sat"},
    {"name": "CHC Wakad Pune", "city": "Pune", "district": "Pune", "state": "Maharashtra",
     "address": "Wakad, Pune 411057", "phone": "+91-20-2729-1234",
     "beds": 50, "icu": 4, "nicu": 0, "emergency": False,
     "caps": ["pathology_lab", "blood_bank", "high_risk_pregnancy"],
     "equip": ["Ultrasound", "Lab"],
     "accr": [], "hours": "OPD 8am-2pm"},
]

# ─── Report templates ────────────────────────────────────────────────────────

def messy_report(f: dict) -> str:
    """Generate a realistic, messy facility report with random quality variation."""
    quality = random.choice(["high", "medium", "low", "very_low"])
    r = random.random

    name = f["name"]
    city = f["city"]
    state = f["state"]

    if quality == "high":
        caps_desc = ", ".join(random.sample(f["caps"], min(len(f["caps"]), 8)))
        equip_desc = "; ".join(f["equip"])
        return f"""FACILITY INSPECTION REPORT
Annual Compliance Filing — {2023 + random.randint(0,1)}

Facility Name: {name}
Address: {f['address']}
Contact: {f['phone']}
State: {state} | District: {f['district']} | City: {city}
Pin Code: {f.get('address', '').split()[-1] if f.get('address') else ''}

Facility Type: {"Multi-specialty Hospital" if f['beds'] > 200 else "Primary Health Centre"}
Total Licensed Beds: {f['beds']}
ICU Beds: {f['icu']}
{"NICU Beds: " + str(f['nicu']) if f['nicu'] else ""}
Emergency Services: {"24x7 Emergency available" if f['emergency'] else "No emergency services"}
Operational Hours: {f['hours']}

ACCREDITATIONS:
{chr(10).join("- " + a for a in f['accr']) if f['accr'] else "- None on file"}

CLINICAL SERVICES & DEPARTMENTS:
The facility provides the following key services: {caps_desc}.

MEDICAL EQUIPMENT:
{equip_desc}

CONTACT:
Phone: {f['phone']}

This report has been verified and submitted as per the Ministry of Health guidelines.
Data is accurate as of {random.choice(["January", "March", "June", "September"])} {2023 + random.randint(0,1)}.
"""

    elif quality == "medium":
        caps_subset = random.sample(f["caps"], max(1, len(f["caps"])//2))
        return f"""{name} — Hospital Summary

Location: {city}, {state}
Phone: {f['phone']}
Beds: {f['beds']} (ICU: {f['icu']})
Emergency 24/7: {"Yes" if f['emergency'] else "No"}

Services available: {", ".join(caps_subset)}

Equipment: {", ".join(f['equip'][:3])}

Accreditations: {", ".join(f['accr']) if f['accr'] else "N/A"}

For more information contact the hospital directly.
"""

    elif quality == "low":
        # Minimal, abbreviation-heavy
        return f"""Name: {name}
Loc: {city} {state}
Ph: {f['phone']}
Beds: {f['beds']}
Svc: {" | ".join([c.replace("_", " ") for c in f['caps'][:4]])}
Emg: {"Y" if f['emergency'] else "N"}
"""

    else:  # very_low
        # Scanned doc simulation — partial, misspellings
        return f"""...[Page break]...

{name}
{city} - {state}
TEL: {f['phone']}

Total bds: {f['beds']}
ICU avlble: {"yes" if f['icu'] > 0 else "no"}
Emgncy: {"round the clock" if f['emergency'] else "OPD only"}

Specl: {random.choice(f['caps']) if f['caps'] else "general"} and more

   ...rest of page not legible...
"""


if __name__ == "__main__":
    count = 0
    for i, facility in enumerate(FACILITIES):
        # Generate 2 report variants per facility (different quality/format)
        for variant in range(2):
            content = messy_report(facility)
            fname = f"{facility['name'].replace(' ', '_').replace('/', '_')[:40]}_v{variant+1}.txt"
            fpath = os.path.join(OUTPUT_DIR, fname)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)
            count += 1

    print(f"[Generate] ✓ Created {count} synthetic facility reports in {OUTPUT_DIR}")
    print(f"           Run 'python scripts/bulk_ingest.py' to ingest them.")
