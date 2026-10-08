from datetime import datetime

attendance_records = []


def mark_attendance(student_name, subject, date, status):
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
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    attendance_records.append(record)
    return record


def get_attendance():
    return attendance_records
