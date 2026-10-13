def compute_skill_match_score(parsed_skills: list[str], required_skills: list[str]) -> float:
    if not required_skills:
        return 0.0

    parsed_set = {s.strip().lower() for s in parsed_skills if s}
    required_set = {s.strip().lower() for s in required_skills if s}

    matched = parsed_set & required_set
    return len(matched)/len(required_set)

def compute_final_score(ats_score: float, skill_match_score: float, github_score: float = 0.0) -> int:
    total = (
        (0.5 * skill_match_score)
        + (0.25 * (ats_score / 100))
        + (0.25 * ((github_score or 0.0) / 100))
    ) * 100
    return int(round(total))
