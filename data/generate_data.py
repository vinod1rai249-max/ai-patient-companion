"""Generate synthetic patient profiles and lab history for local demos."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = DATA_DIR / "synthetic_patients.json"
YEARS_OF_HISTORY = 5
TEST_CATALOG = {
    "HbA1c": {"unit": "%", "normal_range": "4.0-5.6", "low": 4.0, "high": 5.6},
    "Total Cholesterol": {
        "unit": "mg/dL",
        "normal_range": "125-200",
        "low": 125.0,
        "high": 200.0,
    },
    "LDL": {"unit": "mg/dL", "normal_range": "0-100", "low": 0.0, "high": 100.0},
    "HDL": {"unit": "mg/dL", "normal_range": "40-80", "low": 40.0, "high": 80.0},
    "Fasting Glucose": {
        "unit": "mg/dL",
        "normal_range": "70-99",
        "low": 70.0,
        "high": 99.0,
    },
    "TSH": {"unit": "mIU/L", "normal_range": "0.4-4.0", "low": 0.4, "high": 4.0},
    "Creatinine": {
        "unit": "mg/dL",
        "normal_range": "0.6-1.3",
        "low": 0.6,
        "high": 1.3,
    },
    "Hemoglobin": {
        "unit": "g/dL",
        "normal_range": "12.0-17.5",
        "low": 12.0,
        "high": 17.5,
    },
    "WBC": {
        "unit": "10^3/uL",
        "normal_range": "4.0-11.0",
        "low": 4.0,
        "high": 11.0,
    },
}


def classify_lab_status(test_name: str, value: float) -> str:
    """Classify a synthetic lab result using the catalog ranges."""

    definition = TEST_CATALOG[test_name]
    if value < definition["low"]:
        return "LOW"
    if value > definition["high"]:
        return "HIGH"
    return "NORMAL"


def build_lab_result(patient_id: str, test_name: str, value: float, year: int) -> dict[str, str | float]:
    """Create a single synthetic lab result payload."""

    definition = TEST_CATALOG[test_name]
    return {
        "patient_id": patient_id,
        "test_name": test_name,
        "value": round(value, 2),
        "unit": definition["unit"],
        "normal_range": definition["normal_range"],
        "status": classify_lab_status(test_name, value),
        "collected_at": date(year, 6, 15).isoformat(),
    }


def build_patient(patient_id: str, age: int, sex: str, yearly_values: dict[str, list[float]]) -> dict:
    """Create a patient profile with yearly lab history."""

    years = list(range(date.today().year - YEARS_OF_HISTORY + 1, date.today().year + 1))
    lab_results: list[dict[str, str | float]] = []

    for test_name, values in yearly_values.items():
        for year, value in zip(years, values, strict=True):
            lab_results.append(build_lab_result(patient_id, test_name, value, year))

    lab_results.sort(key=lambda item: (item["collected_at"], item["test_name"]))
    return {
        "patient_id": patient_id,
        "age": age,
        "sex": sex,
        "lab_results": lab_results,
    }


def generate_synthetic_dataset() -> list[dict]:
    """Return deterministic synthetic patients with trend-ready lab histories."""

    patients = [
        build_patient(
            patient_id="demo-patient-001",
            age=52,
            sex="female",
            yearly_values={
                "HbA1c": [5.6, 5.9, 6.2, 6.6, 7.0],
                "Total Cholesterol": [175, 188, 202, 219, 236],
                "LDL": [95, 104, 113, 126, 138],
                "HDL": [58, 56, 55, 54, 53],
                "Fasting Glucose": [94, 99, 104, 112, 121],
                "TSH": [2.1, 2.2, 2.4, 2.5, 2.6],
                "Creatinine": [0.82, 0.83, 0.85, 0.86, 0.88],
                "Hemoglobin": [13.5, 13.4, 13.3, 13.2, 13.1],
                "WBC": [6.1, 6.0, 6.2, 6.3, 6.1],
            },
        ),
        build_patient(
            patient_id="demo-patient-002",
            age=39,
            sex="male",
            yearly_values={
                "HbA1c": [5.2, 5.1, 5.2, 5.1, 5.2],
                "Total Cholesterol": [181, 179, 180, 182, 181],
                "LDL": [98, 96, 97, 98, 97],
                "HDL": [52, 53, 52, 54, 53],
                "Fasting Glucose": [89, 88, 90, 89, 90],
                "TSH": [1.8, 1.9, 1.8, 1.7, 1.8],
                "Creatinine": [0.93, 0.94, 0.92, 0.95, 0.94],
                "Hemoglobin": [14.8, 14.7, 14.9, 14.8, 14.8],
                "WBC": [5.8, 5.9, 5.7, 5.8, 5.9],
            },
        ),
        build_patient(
            patient_id="demo-patient-003",
            age=61,
            sex="female",
            yearly_values={
                "HbA1c": [5.4, 5.4, 5.5, 5.4, 5.5],
                "Total Cholesterol": [192, 191, 193, 192, 191],
                "LDL": [101, 100, 102, 101, 100],
                "HDL": [61, 62, 60, 61, 62],
                "Fasting Glucose": [92, 91, 92, 93, 92],
                "TSH": [2.7, 2.8, 2.9, 2.8, 2.7],
                "Creatinine": [0.79, 0.8, 0.81, 0.8, 0.79],
                "Hemoglobin": [12.8, 12.9, 12.7, 12.8, 12.9],
                "WBC": [6.6, 6.5, 6.6, 6.4, 6.5],
            },
        ),
    ]
    return patients


def save_dataset(patients: list[dict], output_path: Path = OUTPUT_PATH) -> Path:
    """Write the synthetic dataset to disk."""

    output_path.write_text(json.dumps(patients, indent=2), encoding="utf-8")
    return output_path


def main() -> None:
    patients = generate_synthetic_dataset()
    save_dataset(patients)

    total_results = sum(len(patient["lab_results"]) for patient in patients)
    print(f"Synthetic data written to {OUTPUT_PATH}")
    print(f"Patients generated: {len(patients)}")
    print(f"Lab results generated: {total_results}")


if __name__ == "__main__":
    main()
