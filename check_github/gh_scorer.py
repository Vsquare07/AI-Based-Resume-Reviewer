from .gh_config import SEV_PENALTY_REPO
def _history_points(n):
    return 25 if n >= 50 else 20 if n >= 15 else 12 if n >= 5 else 5 if n >= 3 else 0

def _lifespan_points(days):
    return 10 if days >= 60 else 7 if days >= 14 else 4 if days >= 2 else 0

def finalize_repo(r):
    m = r["metrics"]
    c = r["components"]
    n = m.get("_total_for_quality", 0)
    c["history_depth"] = _history_points(n)
    c["lifespan"] = _lifespan_points(m.get("lifespan_days", 0)) if not r["is_fork"] else 0
    stars = 0 if r["is_fork"] else m.get("stars", 0)
    c["community"] = 10 if stars >= 10 else 7 if stars >= 3 else 4 if stars >= 1 else 0

    msg = 3 if m.get("_generic_ratio", 0) <= 0.3 else 1 if m.get("_generic_ratio", 0) < 0.7 else 0
    if n < 8:
        msg = 1
    c["engineering"] = (7 if m.get("tests") else 0) + (6 if m.get("ci") else 0) + (4 if m.get("pull_requests") else 0) \
        + (2 if m.get("_license_holder") is not None or any("licen" in p.lower() for p in r["_paths"][:200]) else 0) \
        + (3 if m.get("manifest") else 0) + msg

    share = m.get("own_share", 0)
    if r["is_fork"] or r["owner"].lower() != r["_login_l"]:
        c["own_contribution"] = 5 if m.get("own_commits_est", 0) > 0 else 0
    else:
        c["own_contribution"] = 10 if share >= 0.7 else 6 if share >= 0.4 else 3 if share >= 0.15 else 0

    det = m.get("_readme_points_det", 0)
    llm_doc = (r.get("llm") or {}).get("readme_points")
    c["documentation"] = det + llm_doc if llm_doc is not None else round(det / 14 * 20)

    r["quality_score"] = int(sum(c.values()))
    penalty = sum(SEV_PENALTY_REPO[f["severity"]] for f in r["flags"])
    score = max(0, r["quality_score"] - penalty)
    if r["cap"] is not None:
        score = min(score, r["cap"])
    r["score"] = int(score)
    return r