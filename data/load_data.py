"""Load synthetic patient data into the local SQLite database."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import get_settings
from backend.database import DatabaseManager


DATA_FILE = Path(__file__).resolve().parent / "synthetic_patients.json"


def load_patients_from_file(data_file: Path = DATA_FILE) -> list[dict]:
    """Read synthetic patient data from disk."""

    return json.loads(data_file.read_text(encoding="utf-8"))


def load_data_into_database(
    database_manager: DatabaseManager,
    patients: list[dict],
) -> tuple[int, int]:
    """Insert synthetic patients and lab results into SQLite."""

    database_manager.create_tables()

    patient_records = [
        {
            "patient_id": patient["patient_id"],
            "age": patient["age"],
            "sex": patient["sex"],
        }
        for patient in patients
    ]
    database_manager.bulk_insert_patients(patient_records)

    loaded_lab_results = 0
    for patient in patients:
        database_manager.delete_lab_results_by_patient_id(patient["patient_id"])
        database_manager.bulk_insert_lab_results(patient["lab_results"])
        loaded_lab_results += len(patient["lab_results"])

    return len(patient_records), loaded_lab_results


def main() -> None:
    settings = get_settings()
    database_manager = DatabaseManager(settings.database_url)
    patients = load_patients_from_file()
    patient_count, lab_result_count = load_data_into_database(database_manager, patients)

    print("Synthetic data load completed successfully.")
    print(f"Patients loaded: {patient_count}")
    print(f"Lab results loaded: {lab_result_count}")


if __name__ == "__main__":
    main()
