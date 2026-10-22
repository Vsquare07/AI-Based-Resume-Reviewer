import json
import re
from pathlib import Path

# Core pipeline modules
from ats_scorer import calculate_ats_score
from compare_resumes import load_db
from match_skills import match_skills
from check_github import analyze_github
from helper import compute_skill_match_score, compute_final_score
from inference import build_context_prompt, run_inference, generate_weaknesses

from resume_text_parser import parse_resume

# Paths and configurations
RAG_DB_DIR = "rag_db"
PARSED_RESUME_PATH = "outputs/parsed_resume.json"
RAW_TEXT_PATH = "outputs/raw_resume_text.txt"
DEFAULT_PDF = r"C:\Users\prans\AppData\Local\paolino\zapfast\cache\accounts\1\media\AC282526F5D9EE15746583E637BB1DB4-cv.pdf"
JOB_TITLE = "AI Engineer"
OLLAMA_MODEL = "huihui_ai/qwen3.5-abliterated:9b"


def ensure_sample_data():
    """Generates sample resume data if outputs files are not yet created."""
    out_dir = Path("outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    parsed_path = Path(PARSED_RESUME_PATH)
    raw_path = Path(RAW_TEXT_PATH)

    if not parsed_path.exists():
        sample_parsed = {
            "personal_details": [
                "John Doe",
                "john.doe@email.com",
                "+1 (555) 019-2834",
                "https://github.com/johndoe",
                "https://linkedin.com/in/johndoe"
            ],
            "education": [
                "B.S. in Computer Science, State University, 2020 - 2024"
            ],
            "achievements": [
                "1st place at Regional AI Hackathon 2023"
            ],
            "certificates": [
                "AWS Certified Cloud Practitioner (2023)"
            ],
            "projects": [
                "Neural Search Engine: Built vector search engine using Python, FAISS, and FastAPI (https://github.com/johndoe/neural-search)",
                "Resume Reviewer: Built NLP parser in Python using PyTorch and Flask"
            ],
            "experience": [
                "Machine Learning Intern at TechCorp (2023 - 2024): Developed Python pipelines and improved model inference speed by 25%."
            ],
            "skills": [
                "Python",
                "PyTorch",
                "SQL",
                "Git",
                "FastAPI",
                "Flask",
                "Scikit-learn"
            ]
        }
        parsed_path.write_text(json.dumps(sample_parsed, indent=2), encoding="utf-8")

    if not raw_path.exists():
        sample_raw = """John Doe
john.doe@email.com | +1 (555) 019-2834 | https://github.com/johndoe | https://linkedin.com/in/johndoe

EDUCATION
B.S. in Computer Science, State University, 2020 - 2024

SKILLS
Python, PyTorch, SQL, Git, FastAPI, Flask, Scikit-learn

PROJECTS
Neural Search Engine (https://github.com/johndoe/neural-search)
- Built vector search engine using Python, FAISS, and FastAPI.

Resume Reviewer
- Built NLP parser in Python using PyTorch and Flask.

EXPERIENCE
Machine Learning Intern at TechCorp (2023 - 2024)
- Developed Python pipelines and improved model inference speed by 25%.

ACHIEVEMENTS
- 1st place at Regional AI Hackathon 2023

CERTIFICATES
- AWS Certified Cloud Practitioner (2023)
"""
        raw_path.write_text(sample_raw, encoding="utf-8")


def run_pipeline(
    pdf_path: str | None = None,
    parsed_resume_path: str = PARSED_RESUME_PATH,
    raw_text_path: str = RAW_TEXT_PATH,
    job_title: str = JOB_TITLE
) -> dict:
    """Executes the full AI Resume Reviewer pipeline end-to-end."""
    if pdf_path and Path(pdf_path).exists():
        print("\n[0/4] Parsing resume...")
        parsed_data, raw_text = parse_resume(pdf_path, model=OLLAMA_MODEL)
    else:
        ensure_sample_data()
        with open(parsed_resume_path, "r", encoding="utf-8") as f:
            parsed_data = json.load(f)
        with open(raw_text_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

    print(f"\n[1/4] Running parallel evaluation modules for '{job_title}'...")

    # Module 1: ATS Scoring
    ats_result = calculate_ats_score(raw_text, parsed_data)
    ats_score = ats_result.get("ats_friendliness_score", 0)

    # Module 2: RAG Skill Matching
    db = load_db(RAG_DB_DIR)
    skill_result = match_skills(parsed_data, job_title, db)
    matching_skills = skill_result.get("matching", [])
    missing_skills = skill_result.get("missing", [])

    # Calculate skill match score
    required_skills = [m["skill"] for m in matching_skills + missing_skills]
    all_candidate_skills = list(set(
        [m["skill"] for m in matching_skills] +
        [s if isinstance(s, str) else s.get("skill", "") for s in parsed_data.get("skills", [])]
    ))
    skill_match_score = compute_skill_match_score(all_candidate_skills, required_skills)

    # Module 3: GitHub Code Audit
    github_result = analyze_github(parsed_data)
    github_score = github_result.get("github_score")
    github_flags = github_result.get("flags", [])

    print(f"      - ATS Score: {ats_score}/100")
    print(f"      - Skill Match: {len(matching_skills)} matched, {len(missing_skills)} missing ({skill_match_score*100:.1f}%)")
    print(f"      - GitHub Audit: Score {github_score or 'N/A'}, {len(github_flags)} flags")

    # Module 4: Convergence - AI Inference Evaluation
    print("[2/4] Running AI convergence evaluation...")
    prompt = build_context_prompt(
        raw_text=raw_text,
        job_title=job_title,
        matched_skills=matching_skills,
        missing_skills=missing_skills,
        ats_score=ats_score,
        github_flags=github_flags
    )
    inference_output = run_inference(prompt, model=OLLAMA_MODEL)

    # Module 5: Final Composite Score & Weakness Synthesis
    print("[3/4] Synthesizing final scores and weakness analysis...")
    final_score = compute_final_score(
        ats_score=ats_score,
        skill_match_score=skill_match_score,
        github_score=github_score or 0.0
    )

    weaknesses = generate_weaknesses(
        missing_skills=missing_skills,
        github_flags=github_flags,
        model_reason=inference_output["reason"],
        model_weaknesses=inference_output.get("weaknesses", [])
    )

    # Extract candidate basic info
    personal_details = parsed_data.get("personal_details", [])
    candidate_name = "Candidate"
    if personal_details and len(personal_details) > 0:
        for item in personal_details:
            cleaned = re.sub(r"[^\w\s]", "", item).strip()
            if cleaned and not any(k in item.lower() for k in ["@", "http", "phone", "tel:", "www.", "github.com", "linkedin.com", "(+", "+"]):
                candidate_name = cleaned
                break
        if candidate_name == "Candidate":
            candidate_name = personal_details[0].strip()

    candidate_info = {
        "name": candidate_name,
        "personal_details": personal_details,
        "education": parsed_data.get("education", []),
        "experience": parsed_data.get("experience", []),
    }

    # Module 6: Assemble final schema matching architecture diagram
    output_json = {
        "candidate_name": candidate_name,
        "candidate_info": candidate_info,
        "score": final_score,
        "ats_score": ats_score,
        "github_score": github_score,
        "github_audit": github_result,
        "matched_skills": [m["skill"] for m in matching_skills],
        "missing_skills": [m["skill"] for m in missing_skills],
        "weaknesses": weaknesses,
        "github_flags": [
            f"[{f.get('severity', '').upper()}] {f.get('message')}"
            for f in github_flags
            if f.get("severity") in ("high", "medium")
        ]
    }

    # Save to disk
    out_file = Path("outputs/final_review.json")
    out_file.write_text(json.dumps(output_json, indent=2, ensure_ascii=False), encoding="utf-8")

    print("[4/4] Pipeline completed successfully!")
    return output_json


def main():
    import sys
    pdf_to_run = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF
    target_role = sys.argv[2] if len(sys.argv) > 2 else "Software Engineer"
    result = run_pipeline(pdf_path=pdf_to_run, job_title=target_role)
    print("\n" + "=" * 50)
    print("OUTPUT JSON RETURNED TO FRONTEND")
    print("=" * 50)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
