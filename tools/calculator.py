def calculate_attendance(attended, total):
    try:
        attended = float(attended)
        total = float(total)
    except (TypeError, ValueError):
        raise ValueError("Attended and total classes must be numeric values.")

    if attended < 0:
        raise ValueError("Attended classes cannot be negative.")

    if total <= 0:
        raise ValueError("Total classes must be greater than 0.")

    if attended > total:
        raise ValueError("Attended classes cannot be greater than total classes.")

    percentage = (attended / total) * 100
    return round(percentage, 2)
