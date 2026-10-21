import json
import re
from typing import Literal
from pydantic import BaseModel, Field
from ollama import chat


class InferenceResult(BaseModel):
    reason: str = Field(
        description="Detailed explanation and qualitative assessment of the candidate background against role requirements"
    )
    weaknesses: list[str] = Field(
        default_factory=list,
        description="Specific, actionable candidate weaknesses, competency gaps, or red flags"
    )


def build_context_prompt(
    raw_text: str,
    job_title: str,
    matched_skills: list,
    missing_skills: list,
    ats_score: float | int,
    github_flags: list[dict] | None = None,
    similar_resumes: list[dict] | None = None
) -> str:
    """
    Assembles all candidate signals (resume text, peer benchmark skills, ATS score,
    and GitHub audit flags) into a structured context prompt for the evaluation LLM.
    """
    github_flags = github_flags or []
    similar_resumes = similar_resumes or []

    # Format missing skills (strictly list[dict] from match_skills)
    formatted_missing = [
        f"{m['skill']} (found in {m.get('count', 0)}/{m.get('of', 0)} peer resumes)"
        for m in missing_skills
    ]

    # Format matched skills (strictly list[dict] from match_skills)
    formatted_matched = [
        f"{m['skill']}{'' if m.get('evidenced', True) else ' (listed in skills, but un-evidenced in projects/experience)'}"
        for m in matched_skills
    ]

    # Format GitHub red flags (focus on high and medium severity)
    actionable_flags = [
        f"[{f.get('severity', 'info').upper()}] {f.get('message', '')}" + (f" (repo: {f['repo']})" if f.get('repo') else "")
        for f in github_flags
        if f.get("severity") in ("high", "medium")
    ]
    if not actionable_flags:
        actionable_flags = ["No high or medium severity concerns detected."]

    prompt = f"""You are a senior technical hiring manager and engineering director evaluating a candidate for the role: '{job_title}'.

Carefully evaluate the candidate's resume against the benchmark audit signals below.

### AUDIT SIGNALS
1. Target Role: {job_title}
2. ATS Friendliness Score: {ats_score}/100
3. Matched Skills (Candidate possesses):
   {json.dumps(formatted_matched, ensure_ascii=False)}
4. Missing Skills (Expected by shortlisted peers in this role):
   {json.dumps(formatted_missing, ensure_ascii=False)}
5. Code Authenticity / GitHub Audit Flags:
   {json.dumps(actionable_flags, ensure_ascii=False)}

### CANDIDATE RESUME TEXT
<resume>
{raw_text[:4000]}
</resume>

### EVALUATION INSTRUCTIONS
1. Evaluate whether the candidate has sufficient foundational and practical experience for '{job_title}'.
2. Scrutinize whether claimed skills are backed by real, meaningful projects or work experience rather than keyword stuffing.
3. Weigh the missing benchmark skills and any code authenticity red flags carefully.
4. Provide an objective, professional rationale and qualitative assessment of the candidate's fit for the role.
5. List 2 to 4 concrete, actionable weaknesses explaining *why* specific missing competencies or red flags hurt their candidacy for this role.
"""
    return prompt


def run_inference(
    prompt: str,
    model: str = "qwen3:1.7b"
) -> dict:
    """
    Executes structured inference via Ollama against the built context prompt.
    Returns a dict with keys: 'decision', 'confidence', 'reason', and 'weaknesses'.
    """
    schema = InferenceResult.model_json_schema()

    response = chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are an expert technical evaluator. Output only valid JSON matching the requested schema."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        format=schema,
        think=False,
        options={
            "temperature": 0.1,
            "num_predict": 1000,
            "num_gpu": 99
        },
        keep_alive="30m"
    )

    raw_content = response.message.content or ""
    if not raw_content.strip():
        raise RuntimeError("LLM returned empty inference response.")

    match = re.search(r"\{.*\}", raw_content, re.DOTALL)
    clean_json = match.group(0) if match else raw_content

    validated = InferenceResult.model_validate_json(clean_json)
    return validated.model_dump()


def generate_weaknesses(
    missing_skills: list,
    github_flags: list[dict],
    model_reason: str,
    model_weaknesses: list[str] | None = None
) -> list[str]:
    """
    Consolidates LLM-identified weaknesses with rule-based GitHub flags and missing skills.
    Ensures high-priority flags are never overlooked.
    """
    weaknesses = []

    # Priority 1: High-severity GitHub flags (potential plagiarism, dummy repos, etc.)
    for flag in github_flags:
        if flag.get("severity") == "high":
            where = f" [{flag['repo']}]" if flag.get("repo") else ""
            msg = f"Critical Code Concern{where}: {flag.get('message')}"
            if msg not in weaknesses:
                weaknesses.append(msg)

    # Priority 2: Contextual weaknesses produced by the LLM
    if model_weaknesses:
        for w in model_weaknesses:
            if w not in weaknesses:
                weaknesses.append(w)

    # Fallback if model weaknesses are empty: generate from missing skills & medium flags
    if not model_weaknesses:
        if missing_skills:
            top_missing = [m["skill"] for m in missing_skills[:4]]
            weaknesses.append(f"Missing key role competencies: {', '.join(top_missing)}")

        for flag in github_flags:
            if flag.get("severity") == "medium":
                where = f" [{flag['repo']}]" if flag.get("repo") else ""
                weaknesses.append(f"Code Quality Concern{where}: {flag.get('message')}")

        if model_reason:
            weaknesses.append(f"Recruiter Assessment: {model_reason[:150]}")

    return weaknesses


if __name__ == "__main__":
    sample_prompt = build_context_prompt(
        raw_text="Software engineer with 2 years experience in Python and Flask.",
        job_title="AI Engineer",
        matched_skills=[{"skill": "python", "evidenced": True}],
        missing_skills=[{"skill": "docker", "count": 8, "of": 10}, {"skill": "pytorch", "count": 7, "of": 10}],
        ats_score=75,
        github_flags=[{"severity": "medium", "repo": "face-detector", "message": "1 commit carrying large codebase"}]
    )
    print("Prompt built successfully:")
    print("-" * 50)
    print(sample_prompt)
