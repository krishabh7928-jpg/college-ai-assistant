import json
import os
from datetime import datetime
from pathlib import Path

# Persistent storage file location
if os.getenv("VERCEL"):
    STORAGE_FILE = Path("/tmp/attendance_records.json")
else:
    STORAGE_FILE = Path(__file__).resolve().parent.parent / "attendance_records.json"


def _load_records() -> list[dict[str, str]]:
    if STORAGE_FILE.is_file():
        try:
            return json.loads(STORAGE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_records(records: list[dict[str, str]]) -> None:
    try:
        STORAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STORAGE_FILE.write_text(json.dumps(records, indent=2), encoding="utf-8")
    except Exception:
        pass


def mark_attendance(student_name: str, subject: str, date: str, status: str) -> dict[str, str]:
    if not student_name or not str(student_name).strip():
        raise ValueError("Student name is required.")

    if not subject or not str(subject).strip():
        raise ValueError("Subject is required.")

    if not date:
        raise ValueError("Date is required.")

    normalized_status = str(status).strip().title()
    if normalized_status not in {"Present", "Absent"}:
        raise ValueError("Status must be 'Present' or 'Absent'.")

    record = {
        "student_name": str(student_name).strip(),
        "subject": str(subject).strip(),
        "date": str(date),
        "status": normalized_status,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    records = _load_records()
    records.append(record)
    _save_records(records)
    return record


def get_attendance() -> list[dict[str, str]]:
    return _load_records()
