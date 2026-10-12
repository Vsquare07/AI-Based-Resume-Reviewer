"""
Build the RAG database from the dataset.   Run:  python build_rag.py

Dataset: a CSV with the columns Role and Resume. Every resume is treated as a shortlisted example.
Writes RAG_DIR/records.jsonl, vocab.json and index.faiss.
"""
import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd

from compare_resumes import (EMBEDDING_MODEL, bullet_items, canon, clean_text, detect,
                             evidence_text, make_embed_text, split_sections)

DATASET_PATH = "cleaned_dataset.csv"
RAG_DIR = "rag_db"
MIN_DF = 3        # a skill must be listed in the skills sections of at least this many resumes
MAX_WORDS = 4

# generic words that appear in skills lists but are not skills
STOP = {"etc", "design", "development", "programming languages", "scripting languages", "frameworks",
        "tools", "relational", "electrical", "mechanical", "physics", "compliance", "scalability",
        "rest", "visualization", "including", "other", "others", "operating systems", "version control",
        "collaboration tools", "databases", "cloud platforms", "web development"}
SPLIT = {"html/css": ["html", "css"]}


def skill_items(skills_text):
    """Items from a skills section: 'Category: A, B (C, D)' -> a, b, c, d."""
    out = []
    for line in skills_text.splitlines():
        line = re.sub(r"^[*+\-•\s]+", "", line.strip())
        if ":" in line:
            line = re.sub(r"^[^:()]{2,40}:\s*", "", line)
        for part in re.split(r"[,;]", re.sub(r"[()]", ",", line)):
            item = re.sub(r"\s+", " ", part).strip(" .*").lower()
            item = re.sub(r"^(and|or|including|e\.g\.)\s+", "", item)
            for sub in SPLIT.get(item, [item]):
                sub = canon(sub)
                if (sub and re.search(r"[a-z]", sub) and sub not in STOP
                        and len(sub.split()) <= MAX_WORDS and len(sub) <= 40):
                    out.append(sub)
    return out


def mine_vocab(sections_per_resume):
    df = Counter()
    for sections in sections_per_resume:
        df.update(set(skill_items(sections.get("skills", ""))))
    return [s for s, c in sorted(df.items(), key=lambda x: (-x[1], x[0])) if c >= MIN_DF]


def build_records(roles, texts, vocab):
    records = []
    for i, (role, text) in enumerate(zip(roles, texts)):
        sections = split_sections(text)
        skills = detect(text, vocab)
        used = set(detect(evidence_text(sections, text), vocab))
        projects = [{"text": p[:160], "skills": detect(p, vocab)}
                    for p in bullet_items(sections["projects"])] if sections.get("projects") else []
        records.append({"resume_id": f"r{i:04d}", "role": role, "skills": skills,
                        "evidenced_skills": [s for s in skills if s in used], "projects": projects,
                        "embed_text": make_embed_text(role, skills)})
    return records


def build_rag(dataset_path=DATASET_PATH, rag_dir=RAG_DIR, embedder=None):
    import faiss
    df = pd.read_csv(dataset_path).dropna(subset=["Role", "Resume"]).drop_duplicates(subset=["Resume"])
    roles = df["Role"].astype(str).str.strip().tolist()
    texts = [clean_text(t) for t in df["Resume"]]

    vocab = mine_vocab([split_sections(t) for t in texts])
    records = build_records(roles, texts, vocab)

    if embedder is None:
        from sentence_transformers import SentenceTransformer
        embedder = SentenceTransformer(EMBEDDING_MODEL)
    vectors = embedder.encode([r["embed_text"] for r in records],
                              normalize_embeddings=True).astype("float32")
    index = faiss.IndexFlatIP(vectors.shape[1])   # row i of the index == line i of records.jsonl
    index.add(vectors)

    out = Path(rag_dir)
    out.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(out / "index.faiss"))
    (out / "vocab.json").write_text(json.dumps(vocab))
    with open(out / "records.jsonl", "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return {"resumes": len(records), "skills": len(vocab), "roles": len(set(roles))}


if __name__ == "__main__":
    s = build_rag()
    print(f"{s['resumes']} resumes, {s['roles']} roles, {s['skills']} skills -> {RAG_DIR}/")