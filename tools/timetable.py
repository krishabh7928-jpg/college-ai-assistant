def analyze_timetable(text):
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    return {
        "total_lines": len(lines),
        "content": lines
    }


def find_day_timetable(text, day):
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    day = day.lower()

    results = []

    for line in lines:
        if day in line.lower():
            results.append(line)

    return results