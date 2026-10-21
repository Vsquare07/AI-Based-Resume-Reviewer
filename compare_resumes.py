"""
Shared tools for the RAG skill matcher.

  text -> skills      clean_text, split_sections, detect   (the same code builds the database and reads uploads)
  retrieval           load_db, retrieve                    (similar resumes of the same role)
  comparison          compare                              (matching and missing skills)
"""
import json
import re
from collections import Counter
from pathlib import Path

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# canonical skill -> other spellings. Used when building the vocabulary and when detecting skills.
ALIASES = {
    "aws": ["amazon web services"],
    "azure": ["microsoft azure"],
    "google cloud": ["gcp", "google cloud platform"],
    "kubernetes": ["k8s"],
    "javascript": ["js"],
    "node.js": ["nodejs", "node js"],
    "react": ["reactjs", "react.js"],
    "vue.js": ["vuejs"],
    "html": ["html5"],
    "css": ["css3"],
    "rest apis": ["restful apis", "restful api", "rest api"],
    "ros": ["robot operating system"],
    "postgresql": ["postgres"],
    "c++": ["cpp"],
    "power bi": ["powerbi"],
    "scikit-learn": ["sklearn", "scikit learn"],
    "ssl/tls": ["ssl", "tls"],
    "vpn": ["vpns"],
    "firewalls": ["firewall"],
    "vpc": ["vpcs", "aws vpc"],
    "proof of work": ["pow", "proof-of-work"],
    "proof of stake": ["pos", "proof-of-stake"],
    "byzantine fault tolerance": ["bft"],
    "elliptic curve cryptography": ["ecc"],
    "kalman filter": ["kalman filters"],
    "cloudformation": ["aws cloudformation"],
    "unreal engine": ["unreal engine 4"],
    "truffle suite": ["truffle"],
    "elk": ["elk stack"],
}
ALIAS_TO_CANON = {a: c for c, forms in ALIASES.items() for a in forms}

# one-letter names are ambiguous in prose, so they must appear with exactly this capitalisation
CASE_SENSITIVE = {"c": "C", "r": "R", "go": "Go"}

SECTION_NAMES = {
    "skills": {"skills", "technical skills", "core skills", "tools and technologies", "tools",
               "technical summary", "summary of skills"},
    "experience": {"experience", "professional experience", "work experience"},
    "projects": {"projects", "personal projects", "relevant projects"},
}
HEADER_TO_SECTION = {n: sec for sec, names in SECTION_NAMES.items() for n in names}


def canon(name):
    n = re.sub(r"\s+", " ", name.strip().lower())
    return ALIAS_TO_CANON.get(n, n)


def clean_text(raw):
    """Drop markdown, contact details, the 'Here's a sample resume' line and trailing notes."""
    t = re.sub(r"^\s*(here'?s|here is)[^\n]*\n", "", raw, flags=re.I)
    t = re.sub(r"\[\[([^\]]*)\]\([^)]*\)\]\([^)]*\)", r"\1", t)   # [[a](b)](c)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)                # [a](b)
    t = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[EMAIL]", t)
    t = re.sub(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", "[PHONE]", t)
    t = re.sub(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+/?", "[LINKEDIN]", t)
    t = re.sub(r"\\([*_\[\]()#+.!-])", r"\1", t)                  # A\* algorithm -> A* algorithm
    t = re.sub(r"\*\*|__|`", "", t)
    m = re.search(r"\n\W*(note:|this (resume|structure)|remember|i hope|feel free)", t, re.I)
    return (t[:m.start()] if m else t).strip()


def split_sections(text):
    """{section name: text}. Known sections are 'skills', 'experience', 'projects'."""
    sections, current = {}, "header"
    for line in text.splitlines():
        s = line.strip()
        head = re.sub(r"[*_#`]", "", s).rstrip(":").strip().lower()
        is_bullet = re.match(r"^[*+\-•]\s", s) is not None
        if (not is_bullet and head and len(head) <= 45
                and (head in HEADER_TO_SECTION or s.rstrip("*_ ").endswith(":"))):
            current = HEADER_TO_SECTION.get(head, head)
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def bullet_items(text):
    """One item per bullet line (or per non-empty line if there are no bullets)."""
    bullets = [re.sub(r"^[*+\-•]\s+", "", l.strip()) for l in text.splitlines()
               if re.match(r"^\s*[*+\-•]\s", l)]
    return bullets or [l.strip() for l in text.splitlines() if l.strip()]


def evidence_text(sections, full_text):
    """Text where a skill counts as used: experience and projects, else everything but the skills list."""
    used = "\n".join(sections.get(k, "") for k in ("experience", "projects")).strip()
    if used:
        return used
    skills = sections.get("skills", "")
    return full_text.replace(skills, "") if skills else full_text


def appears(skill, text):
    """Whole-word match of a skill or one of its aliases ('sql' does not match inside 'postgresql')."""
    if skill in CASE_SENSITIVE:
        return re.search(rf"(?<![\w+#.]){re.escape(CASE_SENSITIVE[skill])}(?![\w+#])", text) is not None
    low = text.lower()
    return any(re.search(rf"(?<![a-z0-9+#.]){re.escape(form)}(?![a-z0-9+#])", low)
               for form in [skill] + ALIASES.get(skill, []))


def detect(text, vocab):
    return [s for s in vocab if appears(s, text)]


def make_embed_text(role, skills):
    return f"{role}. Skills: {', '.join(skills[:25])}."


def load_db(rag_dir, embedder=None):
    import faiss
    d = Path(rag_dir)
    records = [json.loads(line) for line in open(d / "records.jsonl")]
    index = faiss.read_index(str(d / "index.faiss"))
    if embedder is None:
        from sentence_transformers import SentenceTransformer
        import torch
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        embedder = SentenceTransformer(EMBEDDING_MODEL, device=device)
    return {"records": records, "vocab": json.load(open(d / "vocab.json")),
            "index": index, "embedder": embedder}


def retrieve(role, skills, db, k=10, min_role_hits=3):
    """The k most similar resumes of the same role. Falls back to the nearest of any role
    when the role is unknown. Returns ([(similarity, record)], same_role)."""
    q = db["embedder"].encode([make_embed_text(role, skills)],
                              normalize_embeddings=True).astype("float32")
    scores, ids = db["index"].search(q, min(len(db["records"]), k * 5))
    ranked = [(float(s), db["records"][i]) for s, i in zip(scores[0], ids[0]) if i >= 0]
    same = [(s, r) for s, r in ranked if r["role"].lower() == role.strip().lower()]
    if len(same) >= min_role_hits:
        return same[:k], True
    return ranked[:k], False


def compare(skills, evidenced, neighbors, same_role, min_share=0.4, min_neighbors=5):
    """matching: skills you have that at least min_share of the neighbors have.
    missing: skills at least min_share of the neighbors have that you don't."""
    n = len(neighbors)
    count = Counter(s for _, r in neighbors for s in set(r["skills"]))
    common = sorted(((s, c) for s, c in count.items() if n and c / n >= min_share),
                    key=lambda x: (-x[1], x[0]))
    mine, used = set(skills), set(evidenced)
    return {
        "matching": [{"skill": s, "count": c, "of": n, "evidenced": s in used}
                     for s, c in common if s in mine],
        "missing": [{"skill": s, "count": c, "of": n} for s, c in common if s not in mine],
        "confidence": {"neighbors": n, "same_role": same_role,
                       "low": n < min_neighbors or not same_role},
    }
