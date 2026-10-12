import re
import json
from text_extractor import extract_text


def contains_keyword(text, keywords):
    text = text.lower()
    return any(keyword.lower() in text for keyword in keywords)


def has_email(text):
    pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    return re.search(pattern, text) is not None


def has_phone_number(text):
    candidates = re.findall(
        r"(?<!\w)\+?\d[\d\s().-]{7,}\d(?!\w)",
        text
    )

    for candidate in candidates:
        digit_count = len(re.sub(r"\D", "", candidate))

        if 10 <= digit_count <= 15:
            return True

    return False


def has_url(text):
    pattern = (
        r"https?://\S+"
        r"|www\.\S+"
        r"|\b(?:linkedin\.com|github\.com)/\S+"
    )
    return re.search(pattern, text, re.IGNORECASE) is not None


def has_date_or_year(text):
    return re.search(r"\b(?:19|20)\d{2}\b", text) is not None


def has_nonempty_value(value):
    """Check whether a field contains at least one non-empty value."""
    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    if isinstance(value, (list, tuple, set)):
        return any(has_nonempty_value(item) for item in value)

    if isinstance(value, dict):
        return any(
            has_nonempty_value(item)
            for item in value.values()
        )

    return bool(value)


def calculate_ats_score(resume_text, extracted_data):

    required_fields = [
        "personal_details",
        "education",
        "achievements",
        "certificates",
        "projects",
        "experience",
        "skills"
    ]

    all_fields_nonempty = all(
        has_nonempty_value(extracted_data.get(field))
        for field in required_fields
    )

    checks = [
        (
            "Email",
            "email" in resume_text.lower()
            or has_email(resume_text),
            10
        ),
        (
            "Phone",
            "phone" in resume_text.lower()
            or has_phone_number(resume_text),
            10
        ),
        (
            "Skills",
            contains_keyword(resume_text, ["skill"]),
            10
        ),
        (
            "Projects",
            contains_keyword(resume_text, ["project"]),
            10
        ),
        (
            "Education",
            contains_keyword(resume_text, ["education"]),
            10
        ),
        (
            "Experience",
            contains_keyword(resume_text, ["experience"]),
            10
        ),
        (
            "Certificates / Qualifications",
            contains_keyword(
                resume_text,
                ["certificate", "certification", "qualification"]
            ),
            5
        ),
        (
            "Achievements",
            contains_keyword(
                resume_text,
                ["achievement", "award", "honor", "honour"]
            ),
            5
        ),
        (
            "URL",
            has_url(resume_text),
            5
        ),
        (
            "Date / Year",
            has_date_or_year(resume_text),
            5
        ),
        (
            "All 7 extracted fields are non-empty",
            all_fields_nonempty,
            20
        )
    ]

    score = sum(
        points
        for _, passed, points in checks
        if passed
    )

    return {
        "ats_friendliness_score": score,
        "max_score": 100,
        "breakdown": [
            {
                "check": name,
                "passed": passed,
                "points_awarded": points if passed else 0,
                "max_points": points
            }
            for name, passed, points in checks
        ]
    }


# Extract the resume text
resume_text = extract_text("sample2.pdf")

with open("parsed_resume.json", "r", encoding="utf-8") as file:
    data = json.load(file)

report = calculate_ats_score(resume_text, data)

print(
    f"ATS Friendliness Score: "
    f"{report['ats_friendliness_score']}/100"
)

for item in report["breakdown"]:
    status = "PASS" if item["passed"] else "FAIL"

    print(
        f"{status}: {item['check']} "
        f"({item['points_awarded']}/{item['max_points']})"
    )

print(json.dumps(report, indent=2, ensure_ascii=False))