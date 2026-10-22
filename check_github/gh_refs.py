import re
from collections import Counter
from .gh_helpers import _walk, _norm, _words
_GH_RE = re.compile(
    r"(?<![\w.-])(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))(?:/([A-Za-z0-9._-]+))?",
    re.I)
_RESERVED = {
    "features", "topics", "orgs", "about", "pricing", "login", "join", "settings", "marketplace",
    "sponsors", "explore", "collections", "enterprise", "apps", "site", "security", "notifications",
    "issues", "pulls", "search", "trending", "readme", "customer-stories", "solutions", "resources",
    "contact", "new", "organizations", "codespaces", "copilot", "events", "stars", "followers",
    "users", "github",
}

def extract_github_refs(extracted_data):
    profiles, repos = [], []
    for field, text in _walk(extracted_data or {}):
        for m in _GH_RE.finditer(text):
            owner, name = m.group(1), m.group(2)
            if owner.lower() in _RESERVED:
                continue
            if name:
                name = name.rstrip(".")
                if name.lower().endswith(".git"):
                    name = name[:-4]
            if name:
                repos.append((owner, name))
            else:
                profiles.append((owner, field))

    username = None
    pd_profiles = [o for o, f in profiles if f == "personal_details"]
    if pd_profiles:
        username = pd_profiles[0]
    elif profiles:
        username = Counter(o.lower() for o, _ in profiles).most_common(1)[0][0]
        username = next(o for o, _ in profiles if o.lower() == username)
    elif repos:
        top = Counter(o.lower() for o, _ in repos).most_common(1)[0][0]
        username = next(o for o, _ in repos if o.lower() == top)

    seen, dedup = set(), []
    for o, n in repos:
        key = (o.lower(), n.lower())
        if key not in seen:
            seen.add(key)
            dedup.append((o, n))
    return {"username": username, "repos": dedup}


_STOP = {"app", "project", "system", "using", "with", "the", "and", "for", "built", "based", "web",
         "api", "tool", "tools", "simple", "basic", "demo", "test", "code", "main", "repo", "new"}

def _name_tokens(name):
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    toks = re.findall(r"[a-z0-9]+", spaced.lower())
    return [t for t in toks if len(t) >= 3 and t not in _STOP]

def match_claims(projects, repo_names, linked):
    out, matched = {}, set()
    for i, p in enumerate(projects):
        p_low = p.lower()
        p_norm = _norm(p)
        p_words = set(_words(p))
        for o, n in linked:
            if f"github.com/{o}/{n}".lower() in p_low:
                out.setdefault(n.lower(), []).append({"text": p, "kind": "url"})
                matched.add(i)
        for rn in repo_names:
            rn_norm = _norm(rn)
            toks = _name_tokens(rn)
            strong = (len(rn_norm) >= 8 and rn_norm in p_norm) or \
                     (len(toks) >= 2 and sum(t in p_words for t in toks) >= 2)
            if strong and not any(c["text"] == p for c in out.get(rn.lower(), [])):
                out.setdefault(rn.lower(), []).append({"text": p, "kind": "name_strong"})
                matched.add(i)
    return out, matched