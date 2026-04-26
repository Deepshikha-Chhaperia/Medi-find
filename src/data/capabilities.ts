import { CapabilityMeta } from "@/types/medifind";

export const CAPABILITY_META: Record<string, CapabilityMeta> = {
  trauma_center: { id: "trauma_center", label: "Trauma Center", category: "Emergency", aliases: ["trauma", "Level I trauma"] },
  stroke_unit: { id: "stroke_unit", label: "Stroke Unit", category: "Emergency", aliases: ["stroke center", "thrombectomy", "tPA"] },
  cardiac_emergency: { id: "cardiac_emergency", label: "Cardiac Emergency", category: "Emergency", aliases: ["cath lab", "primary PCI", "CCU"] },
  poison_control: { id: "poison_control", label: "Poison Control", category: "Emergency", aliases: ["toxicology"] },

  icu_general: { id: "icu_general", label: "ICU (General)", category: "Critical Care", aliases: ["intensive care"] },
  icu_cardiac: { id: "icu_cardiac", label: "Cardiac ICU", category: "Critical Care", aliases: ["CCU", "CICU"] },
  icu_neuro: { id: "icu_neuro", label: "Neuro ICU", category: "Critical Care", aliases: ["NICU brain"] },
  nicu: { id: "nicu", label: "Neonatal ICU", category: "Critical Care", aliases: ["NICU", "newborn ICU", "premature"] },
  picu: { id: "picu", label: "Pediatric ICU", category: "Critical Care", aliases: ["PICU"] },

  mri: { id: "mri", label: "MRI", category: "Diagnostics", aliases: ["3T MRI", "magnetic resonance"] },
  ct_scan: { id: "ct_scan", label: "CT Scan", category: "Diagnostics", aliases: ["CAT scan", "computed tomography"] },
  pet_ct: { id: "pet_ct", label: "PET-CT", category: "Diagnostics", aliases: ["positron emission"] },
  cath_lab: { id: "cath_lab", label: "Cath Lab", category: "Diagnostics", aliases: ["catheterization lab"] },
  pathology_lab: { id: "pathology_lab", label: "Pathology", category: "Diagnostics", aliases: ["lab", "diagnostics"] },

  robotic_surgery: { id: "robotic_surgery", label: "Robotic Surgery", category: "Surgery", aliases: ["da Vinci", "Mako"] },
  cardiac_surgery: { id: "cardiac_surgery", label: "Cardiac Surgery", category: "Surgery", aliases: ["CABG", "bypass"] },
  neurosurgery: { id: "neurosurgery", label: "Neurosurgery", category: "Surgery", aliases: ["brain surgery"] },
  transplant_kidney: { id: "transplant_kidney", label: "Kidney Transplant", category: "Surgery", aliases: ["renal transplant"] },
  transplant_liver: { id: "transplant_liver", label: "Liver Transplant", category: "Surgery", aliases: ["hepatic transplant"] },
  bariatric_surgery: { id: "bariatric_surgery", label: "Bariatric Surgery", category: "Surgery", aliases: ["weight loss surgery"] },

  high_risk_pregnancy: { id: "high_risk_pregnancy", label: "High-Risk Pregnancy", category: "Maternity", aliases: ["MFM", "perinatology"] },
  c_section_24x7: { id: "c_section_24x7", label: "24/7 C-Section", category: "Maternity", aliases: ["emergency cesarean"] },

  radiation_therapy: { id: "radiation_therapy", label: "Radiation Therapy", category: "Cancer Care", aliases: ["radiotherapy", "linac"] },
  chemotherapy: { id: "chemotherapy", label: "Chemotherapy", category: "Cancer Care", aliases: ["chemo", "infusion"] },
  surgical_oncology: { id: "surgical_oncology", label: "Surgical Oncology", category: "Cancer Care", aliases: ["cancer surgery"] },

  dialysis: { id: "dialysis", label: "Dialysis", category: "Specialty", aliases: ["hemodialysis", "renal replacement"] },
  blood_bank: { id: "blood_bank", label: "Blood Bank", category: "Support", aliases: ["transfusion"] },
  burn_unit: { id: "burn_unit", label: "Burn Unit", category: "Specialty", aliases: ["burns center"] },
  psychiatric_unit: { id: "psychiatric_unit", label: "Psychiatric Unit", category: "Specialty", aliases: ["mental health"] },
};

export const CAPABILITY_CATEGORIES = [
  "Emergency",
  "Critical Care",
  "Diagnostics",
  "Surgery",
  "Maternity",
  "Cancer Care",
  "Specialty",
  "Support",
];

export const QUICK_SEARCHES = [
  { label: "Nearest ICU", query: "nearest hospital with general ICU 24/7", caps: ["icu_general"] },
  { label: "NICU", query: "neonatal ICU for premature babies near me", caps: ["nicu"] },
  { label: "Stroke Centre", query: "stroke unit with thrombectomy 24 hours", caps: ["stroke_unit"] },
  { label: "Blood Bank", query: "24 hour licensed blood bank near me", caps: ["blood_bank"] },
  { label: "Dialysis", query: "hemodialysis center accepting new patients", caps: ["dialysis"] },
  { label: "Cancer Treatment", query: "cancer hospital with chemotherapy and radiation", caps: ["chemotherapy", "radiation_therapy"] },
  { label: "Cardiac Cath Lab", query: "primary PCI angioplasty 24x7", caps: ["cardiac_emergency", "cath_lab"] },
  { label: "Trauma Center", query: "Level I trauma center emergency surgery", caps: ["trauma_center"] },
];