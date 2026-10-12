"""
Matching and missing skills for an uploaded, parsed resume.

Set the three values below and run:  python match_skills.py
or call match_skills(resume, role, db) from your own code.
"""
import json
import statistics
from pathlib import Path

from compare_resumes import (bullet_items, clean_text, compare, detect, evidence_text,
                             load_db, retrieve, split_sections)

RAG_DIR = "rag_db"
K = 10                # similar resumes to compare with
MIN_SHARE = 0.4       # a skill counts if at least this share of the similar resumes have it
RELEVANT_MIN = 2      # a project using >= 2 of the role's core skills is relevant, 1 is partly relevant

def read_resume(path):
    text = Path(path).read_text()
    return json.loads(text) if str(path).endswith(".json") else text


def resume_parts(resume):
    """-> (all text, text where skills are used, list of project descriptions)"""
    if isinstance(resume, dict):   # {"section": [lines]}; personal details are ignored
        sections = {k: "\n".join(v) if isinstance(v, list) else str(v or "")
                    for k, v in resume.items() if k != "personal_details"}
        full = clean_text("\n".join(sections.values()))
        used = "\n".join(sections.get(k, "") for k in ("experience", "projects")).strip()
        if not used:
            used = full.replace(sections.get("skills", ""), "")
        p = resume.get("projects", [])
        projects = p if isinstance(p, list) else bullet_items(str(p))
        return full, used, [x for x in projects if str(x).strip()]
    text = clean_text(resume)
    sections = split_sections(text)
    projects = bullet_items(sections["projects"]) if sections.get("projects") else []
    return text, evidence_text(sections, text), projects


def project_relevance(projects, core, vocab):
    out = []
    for text in projects:
        core_used = [s for s in detect(text, vocab) if s in core]
        label = ("relevant" if len(core_used) >= RELEVANT_MIN
                 else "partly relevant" if core_used else "not relevant")
        out.append({"project": text.strip()[:80], "relevance": label, "core_skills_used": core_used})
    return out


def shortlisted_median(neighbors, core, min_with_projects=3):
    """Median number of relevant projects among similar resumes that list projects (None if too few do)."""
    counts = [sum(len(set(p["skills"]) & core) >= RELEVANT_MIN for p in r["projects"])
              for _, r in neighbors if r["projects"]]
    return statistics.median(counts) if len(counts) >= min_with_projects else None


def match_skills(resume, role, db, k=K, min_share=MIN_SHARE):
    full, used_text, projects = resume_parts(resume)
    skills = detect(full, db["vocab"])
    used = set(detect(used_text, db["vocab"]))
    neighbors, same_role = retrieve(role, skills, db, k=k)
    result = compare(skills, [s for s in skills if s in used], neighbors, same_role, min_share)

    core = {m["skill"] for m in result["matching"] + result["missing"]}
    items = project_relevance(projects, core, db["vocab"])
    result["role"] = role
    result["projects"] = {"items": items,
                          "relevant_count": sum(i["relevance"] == "relevant" for i in items),
                          "shortlisted_median_relevant": shortlisted_median(neighbors, core)}
    return result


def format_result(r):
    c = r["confidence"]
    out = [f"Role: {r['role']}   compared with {c['neighbors']} similar resumes"]
    if not c["same_role"]:
        out.append("WARNING: this role is not in the database, so the nearest resumes of any role were used.")
    elif c["low"]:
        out.append("WARNING: few similar resumes, low confidence.")

    out.append("\nMATCHING skills:")
    out += [f"  {m['skill']:<28} {m['count']} of {m['of']}"
            + ("" if m["evidenced"] else "   <- listed, but no job or project shows it")
            for m in r["matching"]] or ["  none"]
    out.append("\nMISSING skills:")
    out += [f"  {m['skill']:<28} {m['count']} of {m['of']}" for m in r["missing"]] or ["  none"]

    pr = r["projects"]
    out.append("\nPROJECTS (by how many of the role's core skills each uses):")
    for i in pr["items"]:
        out.append(f"  [{i['relevance']}] {i['project']}")
        out.append(f"      core skills used: {', '.join(i['core_skills_used']) or 'none'}")
    if not pr["items"]:
        out.append("  no projects found")
    if pr["shortlisted_median_relevant"] is not None:
        out.append(f"  you have {pr['relevant_count']} relevant project(s); "
                   f"similar resumes have a median of {pr['shortlisted_median_relevant']:g}")
    return "\n".join(out)


if __name__ == "__main__":
    RESUME_PATH = "outputs/parsed_resume.json"   # parsed sections as JSON ({"skills": [...], "projects": [...], ...}) or a .txt file
    ROLE = "AI Engineer"
    with open("outputs/retrieve_match_skills.json", "w", encoding="utf-8") as file:
        json.dump(match_skills(read_resume(RESUME_PATH), ROLE, load_db(RAG_DIR)), file, indent=2, ensure_ascii=False)