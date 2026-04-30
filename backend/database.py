"""SQLite database manager for the local proof of concept."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Any


class DatabaseManager:
    """Small database helper focused on local SQLite persistence."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.database_path = self._resolve_sqlite_path(database_url)

    @staticmethod
    def _resolve_sqlite_path(database_url: str) -> Path:
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            raise ValueError("Only sqlite URLs are supported in this project")

        relative_path = database_url[len(prefix) :]
        database_path = Path(relative_path)
        database_path.parent.mkdir(parents=True, exist_ok=True)
        return database_path

    def get_connection(self) -> sqlite3.Connection:
        """Return a SQLite connection with row access by column name."""

        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def create_tables(self) -> None:
        """Create all tables and indexes required by the foundation layer."""

        with self.get_connection() as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS patients (
                    patient_id TEXT PRIMARY KEY,
                    age INTEGER,
                    sex TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS lab_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id TEXT NOT NULL,
                    test_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT,
                    normal_range TEXT NOT NULL,
                    status TEXT NOT NULL,
                    collected_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    patient_id TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    patient_id TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    assistant_response TEXT NOT NULL,
                    latency_ms REAL,
                    safety_triggers TEXT,
                    safety_triggered INTEGER DEFAULT 0,
                    model_provider TEXT,
                    model_name TEXT,
                    response_quality TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES chat_sessions(session_id),
                    FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    patient_id TEXT NOT NULL,
                    rating TEXT NOT NULL,
                    comment TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES chat_sessions(session_id),
                    FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
                )
                """
            )

            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_patients_patient_id ON patients(patient_id)",
                "CREATE INDEX IF NOT EXISTS idx_lab_results_patient_id ON lab_results(patient_id)",
                "CREATE INDEX IF NOT EXISTS idx_lab_results_test_name ON lab_results(test_name)",
                "CREATE INDEX IF NOT EXISTS idx_chat_sessions_patient_id ON chat_sessions(patient_id)",
                "CREATE INDEX IF NOT EXISTS idx_interactions_session_id ON interactions(session_id)",
                "CREATE INDEX IF NOT EXISTS idx_interactions_patient_id ON interactions(patient_id)",
                "CREATE INDEX IF NOT EXISTS idx_feedback_session_id ON feedback(session_id)",
                "CREATE INDEX IF NOT EXISTS idx_feedback_patient_id ON feedback(patient_id)",
            ]
            for statement in indexes:
                cursor.execute(statement)

            self._ensure_interactions_columns(connection)
            connection.commit()

    @staticmethod
    def _ensure_interactions_columns(connection: sqlite3.Connection) -> None:
        existing_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(interactions)").fetchall()
        }
        column_statements = {
            "safety_triggered": "ALTER TABLE interactions ADD COLUMN safety_triggered INTEGER DEFAULT 0",
            "model_provider": "ALTER TABLE interactions ADD COLUMN model_provider TEXT",
            "model_name": "ALTER TABLE interactions ADD COLUMN model_name TEXT",
        }
        for column_name, statement in column_statements.items():
            if column_name not in existing_columns:
                connection.execute(statement)

    def upsert_patient(self, patient_id: str, age: int | None, sex: str | None) -> None:
        with self.get_connection() as connection:
            connection.execute(
                """
                INSERT INTO patients (patient_id, age, sex)
                VALUES (?, ?, ?)
                ON CONFLICT(patient_id) DO UPDATE SET
                    age = COALESCE(excluded.age, patients.age),
                    sex = COALESCE(excluded.sex, patients.sex)
                """,
                (patient_id, age, sex),
            )
            connection.commit()

    def insert_patient(self, patient_id: str, age: int | None, sex: str | None) -> None:
        """Insert or update a patient record."""

        self.upsert_patient(patient_id=patient_id, age=age, sex=sex)

    def bulk_insert_patients(self, patients: list[dict[str, Any]]) -> None:
        """Insert or update many patient records."""

        with self.get_connection() as connection:
            connection.executemany(
                """
                INSERT INTO patients (patient_id, age, sex)
                VALUES (:patient_id, :age, :sex)
                ON CONFLICT(patient_id) DO UPDATE SET
                    age = COALESCE(excluded.age, patients.age),
                    sex = COALESCE(excluded.sex, patients.sex)
                """,
                patients,
            )
            connection.commit()

    def insert_lab_result(
        self,
        patient_id: str,
        test_name: str,
        value: float,
        unit: str | None,
        normal_range: str,
        status: str,
        collected_at: str | None,
    ) -> None:
        """Insert a single lab result."""

        with self.get_connection() as connection:
            connection.execute(
                """
                INSERT INTO lab_results (
                    patient_id,
                    test_name,
                    value,
                    unit,
                    normal_range,
                    status,
                    collected_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    patient_id,
                    test_name,
                    value,
                    unit,
                    normal_range,
                    status,
                    collected_at,
                ),
            )
            connection.commit()

    def bulk_insert_lab_results(self, lab_results: list[dict[str, Any]]) -> None:
        """Insert many lab results efficiently."""

        with self.get_connection() as connection:
            connection.executemany(
                """
                INSERT INTO lab_results (
                    patient_id,
                    test_name,
                    value,
                    unit,
                    normal_range,
                    status,
                    collected_at
                )
                VALUES (
                    :patient_id,
                    :test_name,
                    :value,
                    :unit,
                    :normal_range,
                    :status,
                    :collected_at
                )
                """,
                lab_results,
            )
            connection.commit()

    def delete_lab_results_by_patient_id(self, patient_id: str) -> None:
        """Remove existing lab results for a patient before reloading demo data."""

        with self.get_connection() as connection:
            connection.execute(
                "DELETE FROM lab_results WHERE patient_id = ?",
                (patient_id,),
            )
            connection.commit()

    def fetch_lab_results_by_patient_id(self, patient_id: str) -> list[dict[str, Any]]:
        """Fetch all lab results for one patient ordered by collection date."""

        with self.get_connection() as connection:
            rows = connection.execute(
                """
                SELECT patient_id, test_name, value, unit, normal_range, status, collected_at
                FROM lab_results
                WHERE patient_id = ?
                ORDER BY collected_at ASC, test_name ASC
                """,
                (patient_id,),
            ).fetchall()

        return [dict(row) for row in rows]

    def fetch_lab_results_by_patient_id_and_test_name(
        self,
        patient_id: str,
        test_name: str,
    ) -> list[dict[str, Any]]:
        """Fetch lab history for a single patient and test."""

        with self.get_connection() as connection:
            rows = connection.execute(
                """
                SELECT patient_id, test_name, value, unit, normal_range, status, collected_at
                FROM lab_results
                WHERE patient_id = ? AND test_name = ?
                ORDER BY collected_at ASC
                """,
                (patient_id, test_name),
            ).fetchall()

        return [dict(row) for row in rows]

    def fetch_patient_profile(self, patient_id: str) -> dict[str, Any] | None:
        """Return only the privacy-scoped patient profile fields."""

        with self.get_connection() as connection:
            row = connection.execute(
                """
                SELECT patient_id, age, sex
                FROM patients
                WHERE patient_id = ?
                """,
                (patient_id,),
            ).fetchone()

        return dict(row) if row else None

    def fetch_recent_completed_lab_results(
        self,
        patient_id: str,
        limit: int = 20,
        max_years: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Return recent completed lab results for the privacy-scoped patient context.

        In this synthetic demo dataset, a lab result is treated as completed when it
        has a non-null `collected_at` value.
        """

        cutoff_date = self._build_cutoff_date(max_years=max_years)
        with self.get_connection() as connection:
            rows = connection.execute(
                """
                SELECT patient_id, test_name, value, unit, normal_range, status, collected_at
                FROM lab_results
                WHERE patient_id = ?
                  AND collected_at IS NOT NULL
                  AND collected_at >= ?
                ORDER BY collected_at DESC, test_name ASC
                LIMIT ?
                """,
                (patient_id, cutoff_date, limit),
            ).fetchall()

        return [dict(row) for row in rows]

    @staticmethod
    def _build_cutoff_date(max_years: int) -> str:
        today = date.today()
        try:
            cutoff = today.replace(year=today.year - max_years)
        except ValueError:
            cutoff = today.replace(month=2, day=28, year=today.year - max_years)
        return cutoff.isoformat()

    def create_chat_session(self, session_id: str, patient_id: str) -> None:
        with self.get_connection() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO chat_sessions (session_id, patient_id)
                VALUES (?, ?)
                """,
                (session_id, patient_id),
            )
            connection.execute(
                """
                UPDATE chat_sessions
                SET updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
                """,
                (session_id,),
            )
            connection.commit()

    def log_interaction(
        self,
        session_id: str,
        patient_id: str,
        user_message: str,
        assistant_response: str,
        latency_ms: float,
        safety_triggers: str = "",
        response_quality: str = "placeholder",
    ) -> None:
        with self.get_connection() as connection:
            connection.execute(
                """
                INSERT INTO interactions (
                    session_id,
                    patient_id,
                    user_message,
                    assistant_response,
                    latency_ms,
                    safety_triggers,
                    response_quality
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    patient_id,
                    user_message,
                    assistant_response,
                    latency_ms,
                    safety_triggers,
                    response_quality,
                ),
            )
            connection.commit()

    def insert_interaction(
        self,
        session_id: str,
        patient_id: str,
        user_message: str,
        assistant_response: str,
        latency_ms: float,
        safety_triggered: bool,
        model_provider: str,
        model_name: str,
        safety_triggers: str = "",
        response_quality: str = "deterministic_orchestrator",
    ) -> None:
        with self.get_connection() as connection:
            connection.execute(
                """
                INSERT INTO interactions (
                    session_id,
                    patient_id,
                    user_message,
                    assistant_response,
                    latency_ms,
                    safety_triggers,
                    safety_triggered,
                    model_provider,
                    model_name,
                    response_quality
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    patient_id,
                    user_message,
                    assistant_response,
                    latency_ms,
                    safety_triggers,
                    int(safety_triggered),
                    model_provider,
                    model_name,
                    response_quality,
                ),
            )
            connection.commit()

    def fetch_interactions_by_session_id(self, session_id: str) -> list[dict[str, Any]]:
        with self.get_connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    session_id,
                    patient_id,
                    user_message,
                    assistant_response,
                    latency_ms,
                    safety_triggers,
                    safety_triggered,
                    model_provider,
                    model_name,
                    created_at
                FROM interactions
                WHERE session_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (session_id,),
            ).fetchall()

        return [dict(row) for row in rows]

    def save_feedback(
        self,
        session_id: str,
        patient_id: str,
        rating: str,
        comment: str | None,
    ) -> None:
        with self.get_connection() as connection:
            connection.execute(
                """
                INSERT INTO feedback (session_id, patient_id, rating, comment)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, patient_id, rating, comment),
            )
            connection.commit()

    def fetch_feedback_by_session(self, session_id: str) -> list[dict[str, Any]]:
        with self.get_connection() as connection:
            rows = connection.execute(
                """
                SELECT session_id, patient_id, rating, comment, created_at
                FROM feedback
                WHERE session_id = ?
                ORDER BY created_at ASC
                """,
                (session_id,),
            ).fetchall()

        return [dict(row) for row in rows]
