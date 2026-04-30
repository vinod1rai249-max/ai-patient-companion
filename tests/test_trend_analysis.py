from backend.database import DatabaseManager
from data.generate_data import generate_synthetic_dataset
from data.load_data import load_data_into_database
from tests.test_data_pipeline import make_database_url, make_scratch_path
from tools.lab_tools import LabTools


def build_lab_tools() -> LabTools:
    database_manager = DatabaseManager(make_database_url(make_scratch_path("trend.db")))
    database_manager.create_tables()
    load_data_into_database(database_manager, generate_synthetic_dataset())
    return LabTools(database_manager=database_manager)


def test_hba1c_trend_for_demo_patient_001_is_increasing() -> None:
    lab_tools = build_lab_tools()

    trend = lab_tools.calculate_lab_trend("demo-patient-001", "HbA1c")

    assert trend["direction"] == "increasing"
    assert trend["first_value"] == 5.6
    assert trend["latest_value"] == 7.0


def test_total_cholesterol_trend_for_demo_patient_001_is_increasing() -> None:
    lab_tools = build_lab_tools()

    trend = lab_tools.calculate_lab_trend("demo-patient-001", "Total Cholesterol")

    assert trend["direction"] == "increasing"
    assert trend["latest_value"] == 236.0


def test_stable_patient_trend_returns_stable_when_within_threshold() -> None:
    lab_tools = build_lab_tools()

    trend = lab_tools.calculate_lab_trend("demo-patient-002", "HbA1c")

    assert trend["direction"] == "stable"


def test_missing_patient_id_returns_safe_result() -> None:
    lab_tools = build_lab_tools()

    trend = lab_tools.calculate_lab_trend("", "HbA1c")

    assert trend["direction"] == "insufficient_data"
    assert trend["total_results"] == 0


def test_missing_test_name_returns_safe_result() -> None:
    lab_tools = build_lab_tools()

    trend = lab_tools.calculate_lab_trend("demo-patient-001", "")

    assert trend["direction"] == "insufficient_data"
    assert trend["total_results"] == 0


def test_single_data_point_returns_insufficient_data() -> None:
    database_manager = DatabaseManager(make_database_url(make_scratch_path("single-point.db")))
    database_manager.create_tables()
    database_manager.insert_patient("single-point-patient", 45, "female")
    database_manager.insert_lab_result(
        patient_id="single-point-patient",
        test_name="HbA1c",
        value=5.7,
        unit="%",
        normal_range="4.0-5.6",
        status="HIGH",
        collected_at="2026-06-15",
    )
    lab_tools = LabTools(database_manager=database_manager)

    trend = lab_tools.calculate_lab_trend("single-point-patient", "HbA1c")

    assert trend["direction"] == "insufficient_data"
    assert trend["total_results"] == 1


def test_lab_results_are_sorted_by_date_before_trend_calculation() -> None:
    database_manager = DatabaseManager(make_database_url(make_scratch_path("sorting.db")))
    database_manager.create_tables()
    database_manager.insert_patient("sorting-patient", 49, "male")
    database_manager.insert_lab_result(
        patient_id="sorting-patient",
        test_name="HbA1c",
        value=6.4,
        unit="%",
        normal_range="4.0-5.6",
        status="HIGH",
        collected_at="2026-06-15",
    )
    database_manager.insert_lab_result(
        patient_id="sorting-patient",
        test_name="HbA1c",
        value=5.8,
        unit="%",
        normal_range="4.0-5.6",
        status="HIGH",
        collected_at="2022-06-15",
    )
    lab_tools = LabTools(database_manager=database_manager)

    trend = lab_tools.calculate_lab_trend("sorting-patient", "HbA1c")

    assert trend["first_date"] == "2022-06-15"
    assert trend["latest_date"] == "2026-06-15"
    assert trend["direction"] == "increasing"


def test_abnormal_values_are_counted_correctly() -> None:
    lab_tools = build_lab_tools()
    results = lab_tools.get_lab_results_by_test("demo-patient-001", "HbA1c")

    abnormal_summary = lab_tools.flag_abnormal_values(results)

    assert abnormal_summary["total_results"] == 5
    assert abnormal_summary["abnormal_count"] == 4
    assert abnormal_summary["critical_count"] == 0


def test_abnormal_results_can_be_extracted_from_scoped_context() -> None:
    lab_tools = build_lab_tools()
    recent_results = lab_tools.database_manager.fetch_recent_completed_lab_results("demo-patient-001")

    abnormal_results = lab_tools.get_abnormal_results_from_scoped_context(recent_results)

    assert abnormal_results
    assert all(result["status"] in {"HIGH", "LOW", "CRITICAL"} for result in abnormal_results)
    assert all("trend_direction" in result for result in abnormal_results)


def test_missing_patient_and_test_return_empty_results() -> None:
    lab_tools = build_lab_tools()

    assert lab_tools.get_patient_lab_results("missing-patient") == []
    assert lab_tools.get_lab_results_by_test("demo-patient-001", "Missing Test") == []
