from datetime import date
from pathlib import Path
from uuid import uuid4

from backend.database import DatabaseManager
from data.generate_data import generate_synthetic_dataset, save_dataset
from data.load_data import load_data_into_database


TEST_OUTPUT_DIR = Path(__file__).resolve().parent / "_artifacts"


def make_database_url(database_path: Path) -> str:
    return f"sqlite:///{database_path.as_posix()}"


def make_scratch_path(file_name: str) -> Path:
    TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return TEST_OUTPUT_DIR / f"{uuid4()}-{file_name}"


def test_synthetic_data_generation_contains_expected_profiles() -> None:
    patients = generate_synthetic_dataset()

    assert len(patients) >= 3
    assert all("patient_id" in patient for patient in patients)
    assert all(len(patient["lab_results"]) == 45 for patient in patients)


def test_save_dataset_writes_json_file() -> None:
    output_path = make_scratch_path("synthetic_patients.json")

    saved_path = save_dataset(generate_synthetic_dataset(), output_path=output_path)

    assert saved_path.exists()
    assert saved_path.read_text(encoding="utf-8").startswith("[")


def test_database_insert_and_fetch_lab_results() -> None:
    database_manager = DatabaseManager(make_database_url(make_scratch_path("test.db")))
    database_manager.create_tables()
    database_manager.insert_patient("patient-001", 50, "female")
    database_manager.insert_lab_result(
        patient_id="patient-001",
        test_name="HbA1c",
        value=5.8,
        unit="%",
        normal_range="4.0-5.6",
        status="HIGH",
        collected_at="2026-06-15",
    )

    rows = database_manager.fetch_lab_results_by_patient_id("patient-001")

    assert len(rows) == 1
    assert rows[0]["test_name"] == "HbA1c"
    assert rows[0]["status"] == "HIGH"


def test_at_least_one_patient_has_trend_ready_hba1c_history() -> None:
    patients = generate_synthetic_dataset()
    trend_patient = next(patient for patient in patients if patient["patient_id"] == "demo-patient-001")
    hba1c_values = [
        result["value"]
        for result in trend_patient["lab_results"]
        if result["test_name"] == "HbA1c"
    ]

    assert len(hba1c_values) == 5
    assert hba1c_values == sorted(hba1c_values)
    assert hba1c_values[-1] > hba1c_values[0]


def test_fetch_by_patient_id_and_test_name_returns_only_requested_history() -> None:
    database_manager = DatabaseManager(make_database_url(make_scratch_path("history.db")))
    database_manager.create_tables()
    patients = generate_synthetic_dataset()
    load_data_into_database(database_manager, patients)

    rows = database_manager.fetch_lab_results_by_patient_id_and_test_name(
        patient_id="demo-patient-001",
        test_name="HbA1c",
    )

    assert len(rows) == 5
    assert all(row["patient_id"] == "demo-patient-001" for row in rows)
    assert all(row["test_name"] == "HbA1c" for row in rows)
    assert rows[0]["collected_at"] < rows[-1]["collected_at"]


def test_synthetic_data_uses_demo_identifiers_only() -> None:
    patients = generate_synthetic_dataset()

    assert all(patient["patient_id"].startswith("demo-patient-") for patient in patients)


def test_recent_completed_lab_results_are_limited_to_20_and_within_5_years() -> None:
    database_manager = DatabaseManager(make_database_url(make_scratch_path("recent.db")))
    database_manager.create_tables()
    load_data_into_database(database_manager, generate_synthetic_dataset())

    rows = database_manager.fetch_recent_completed_lab_results("demo-patient-001", limit=20, max_years=5)

    assert len(rows) <= 20
    collected_dates = [row["collected_at"] for row in rows]
    assert collected_dates == sorted(collected_dates, reverse=True)

    cutoff = date.today().replace(year=date.today().year - 5)
    assert all(row["collected_at"] >= cutoff.isoformat() for row in rows)


def test_fetch_patient_profile_returns_only_age_and_sex_context() -> None:
    database_manager = DatabaseManager(make_database_url(make_scratch_path("profile.db")))
    database_manager.create_tables()
    load_data_into_database(database_manager, generate_synthetic_dataset())

    profile = database_manager.fetch_patient_profile("demo-patient-001")

    assert profile is not None
    assert set(profile.keys()) == {"patient_id", "age", "sex"}
