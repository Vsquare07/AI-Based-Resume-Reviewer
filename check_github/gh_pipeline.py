import os
import re
from collections import Counter
from datetime import datetime, timezone
from .gh_config import (
    SEV_PENALTY_PROFILE, PROFILE_PENALTY_CAP, NEW_ACCOUNT_DAYS, MOSTLY_FORKS_RATIO,
)
from .gh_helpers import _flag, _parse_dt, _norm, _walk, scan_injection
from .gh_client import GitHubClient, GitHubError, NotFound, RateLimited, BudgetExceeded
from .gh_refs import extract_github_refs, match_claims
from .gh_analyzer import analyze_repo
from .gh_scorer import finalize_repo
from .gh_llm import run_llm_for_repo

_LANG_ALIASES = {
    "python": "Python", "py": "Python", "javascript": "JavaScript", "js": "JavaScript", "typescript": "TypeScript",
    "ts": "TypeScript", "java": "Java", "kotlin": "Kotlin", "swift": "Swift", "rust": "Rust", "go": "Go",
    "golang": "Go", "ruby": "Ruby", "php": "PHP", "scala": "Scala", "dart": "Dart", "lua": "Lua", "c": "C",
    "c++": "C++", "cpp": "C++", "c#": "C#", "csharp": "C#", "matlab": "MATLAB", "r": "R", "html": "HTML",
    "css": "CSS", "shell": "Shell", "bash": "Shell", "solidity": "Solidity", "verilog": "Verilog", "vhdl": "VHDL",
    "haskell": "Haskell", "julia": "Julia", "perl": "Perl", "assembly": "Assembly",
}

def _claimed_languages(extracted_data):
    langs = set()
    for _, text in _walk((extracted_data or {}).get("skills")):
        for tok in re.findall(r"[A-Za-z][A-Za-z+#]*", text):
            lang = _LANG_ALIASES.get(tok.lower())
            if lang:
                langs.add(lang)
    return langs

def _name_matches(resume_name, profile_name, login):
    rt = [t for t in re.findall(r"[a-z]+", (resume_name or "").lower()) if len(t) >= 2]
    pt = [t for t in re.findall(r"[a-z]+", (profile_name or "").lower()) if len(t) >= 2]
    if not rt:
        return None
    if set(rt) & set(pt):
        return True
    ln = _norm(login)
    if any(len(t) >= 3 and t in ln for t in rt) or _norm(profile_name) in _norm(resume_name) and _norm(profile_name):
        return True
    return False if profile_name else None

def _select(all_repos, linked, claims_by_repo, username, max_repos):
    by_name = {r["name"].lower(): r for r in all_repos}
    specs, seen = [], set()

    def add(owner, name, repo, why):
        key = (owner.lower(), name.lower())
        if key in seen or len(specs) >= max_repos:
            return
        seen.add(key)
        specs.append({"owner": owner, "name": name, "repo": repo, "why": why})

    for o, n in linked:
        add(o, n, by_name.get(n.lower()) if o.lower() == username.lower() else None, "linked in resume")
    for lname in claims_by_repo:
        if lname in by_name:
            add(by_name[lname]["owner"]["login"], by_name[lname]["name"], by_name[lname], "matches a resume project")
    originals = [r for r in all_repos if not r.get("fork") and r.get("size", 1) > 0
                 and r["name"].lower() != username.lower() and not r["name"].lower().endswith(".github.io")]
    originals.sort(key=lambda r: (r.get("pushed_at") or ""), reverse=True)
    for r in originals:
        add(r["owner"]["login"], r["name"], r, "recently active original repo")
    return specs

def _analyze_github_full(extracted_data, resume_name=None, resume_email=None, claimed_years=None,
                         token=None, llm_fn=None, max_repos=4, max_api_calls=None, client=None, now=None):
    now = now or datetime.now(timezone.utc)
    res = {"status": None, "username": None, "profile_url": None, "github_score": None, "risk_level": None,
           "flags": [], "verified_signals": [], "repos": [], "skills": {"confirmed": [], "unconfirmed": []},
           "llm": {"used": False, "model": None}, "warnings": [], "api_calls": 0}

    refs = extract_github_refs(extracted_data)
    username = refs["username"]
    if not username:
        res["status"] = "not_provided"
        res["warnings"].append("No GitHub link in the resume: no verification possible (not penalised).")
        return res
    res["username"] = username
    res["profile_url"] = f"https://github.com/{username}"

    if client is None:
        auth = bool(token or os.environ.get("GITHUB_TOKEN"))
        client = GitHubClient(token=token, max_calls=max_api_calls or (150 if auth else 40))
    if not getattr(client, "authenticated", True):
        res["warnings"].append("No GITHUB_TOKEN set: limited to ~60 API requests/hour, results may be partial.")

    pflags = []

    def padd(fid, msg, evidence=None):
        pflags.append(_flag(fid, msg, "profile", None, evidence))

    def finish(status):
        res["status"] = status
        res["api_calls"] = getattr(client, "calls", 0)
        return _aggregate(res, pflags)

    try:
        profile = client.get(f"/users/{username}")[0]
    except NotFound:
        padd("PROFILE_NOT_FOUND", f"GitHub profile '{username}' does not exist.")
        return finish("not_found")
    except (RateLimited, BudgetExceeded) as e:
        res["warnings"].append(f"Stopped before analysis: {e}")
        return finish("error")
    except GitHubError as e:
        res["warnings"].append(f"Could not read profile: {e}")
        return finish("error")

    username = profile.get("login", username)
    res["username"] = username
    if profile.get("type") and profile["type"] != "User":
        padd("PROFILE_NOT_A_USER", "Linked profile is an organization, not a person.")
        return finish("not_a_user_profile")

    created = _parse_dt(profile.get("created_at"))
    acct_days = (now - created).days if created else None
    if acct_days is not None and acct_days < NEW_ACCOUNT_DAYS:
        padd("NEW_ACCOUNT", f"Account is only {acct_days} days old.")
    if claimed_years and acct_days is not None and acct_days / 365 + 2 < claimed_years:
        padd("ACCOUNT_YOUNGER_THAN_CLAIM",
             f"Account is {acct_days / 365:.1f} years old vs {claimed_years} years of claimed experience.",
             "Soft signal: people use other accounts.")
    bio_hit = scan_injection(profile.get("bio") or "")
    if bio_hit:
        padd("PROMPT_INJECTION_ATTEMPT", "Text aimed at an AI scorer found in the GitHub bio.", bio_hit)

    try:
        all_repos = client.get(f"/users/{username}/repos", {"per_page": 100, "sort": "pushed", "type": "owner"})[0]
    except (RateLimited, BudgetExceeded, GitHubError) as e:
        res["warnings"].append(f"Could not list repositories: {e}")
        return finish("error")

    if not all_repos and not refs["repos"]:
        padd("NO_PUBLIC_REPOS", "Profile exists but has no public repositories.")
        return finish("analyzed")
    if all_repos and len(all_repos) >= 3 and sum(1 for r in all_repos if r.get("fork")) / len(all_repos) > MOSTLY_FORKS_RATIO:
        padd("MOSTLY_FORKS", "Most public repositories are forks.")

    projects = [t for _, t in _walk((extracted_data or {}).get("projects"))]
    repo_names = [r["name"] for r in all_repos] + [n for _, n in refs["repos"]]
    claims_by_repo, matched_idx = match_claims(projects, repo_names, refs["repos"])
    unmatched = [p for i, p in enumerate(projects) if i not in matched_idx and "github.com" not in p.lower()]
    if unmatched:
        padd("CLAIM_NOT_FOUND", f"{len(unmatched)} resume project(s) match no repository (could be private work).",
             "; ".join(u[:60] for u in unmatched[:3]))

    own_names = {_norm(username), _norm(profile.get("name")), _norm(resume_name)} - {""}
    own_name_norms = set(own_names)
    for src in (profile.get("name"), resume_name):
        for t in re.findall(r"[A-Za-z]+", src or ""):
            if len(t) >= 3:
                own_name_norms.add(t.lower())
    ctx = {"login": username, "login_l": username.lower(), "now": now,
           "own_emails": {e.lower() for e in (profile.get("email"), resume_email) if e},
           "own_names": own_names, "own_name_norms": own_name_norms}

    specs = _select(all_repos, refs["repos"], claims_by_repo, username, max_repos)
    for spec in specs:
        repo = spec["repo"]
        try:
            if repo is None:
                repo = client.get(f"/repos/{spec['owner']}/{spec['name']}")[0]
            claims = claims_by_repo.get(spec["name"].lower(), [])
            r = analyze_repo(client, repo, ctx, claims)
            r["_login_l"] = ctx["login_l"]
            r["_description"] = repo.get("description") or ""
            r["why_selected"] = spec["why"]
            res["repos"].append(r)
        except NotFound:
            res["warnings"].append(f"Linked repository {spec['owner']}/{spec['name']} not found.")
        except (RateLimited, BudgetExceeded) as e:
            res["warnings"].append(f"Stopped early ({e}); results are partial.")
            res["status"] = "partial"
            break
        except GitHubError as e:
            res["warnings"].append(f"{spec['owner']}/{spec['name']}: {e}")

    if llm_fn and res["repos"]:
        res["llm"]["used"] = True
        for r in res["repos"]:
            run_llm_for_repo(r, r["_description"], llm_fn)

    originals = [r for r in res["repos"] if not r["is_fork"] and r["owner"].lower() == username.lower()]
    if not originals and res["repos"] == []:
        padd("NO_ORIGINAL_REPOS", "No original repositories could be analysed.")
    claimed_langs = _claimed_languages(extracted_data)
    if claimed_langs and originals:
        total_bytes = Counter()
        for r in originals:
            total_bytes.update(r["metrics"].get("languages", {}))
        tb = sum(total_bytes.values()) or 1
        confirmed = sorted(l for l in claimed_langs if total_bytes.get(l, 0) / tb >= 0.01 or total_bytes.get(l, 0) >= 5000)
        res["skills"] = {"confirmed": confirmed, "unconfirmed": sorted(claimed_langs - set(confirmed))}
        if len(claimed_langs) >= 4 and len(originals) >= 2 and len(confirmed) / len(claimed_langs) < 0.3:
            padd("SKILL_LANGUAGE_MISMATCH",
                 f"Only {len(confirmed)} of {len(claimed_langs)} claimed languages appear in the analysed repos.",
                 "Private repos are not visible, so this is a soft signal.")

    nm = _name_matches(resume_name, profile.get("name"), username)
    if nm is False:
        padd("IDENTITY_NAME_MISMATCH", "GitHub display name and login share nothing with the resume name.",
             f"profile name: {profile.get('name')!r}")
    if resume_email:
        emails = {e for r in res["repos"] for e in r["metrics"].get("author_emails", [])} | \
                 ({profile["email"].lower()} if profile.get("email") else set())
        if resume_email.lower() in emails:
            res["verified_signals"].append({"id": "IDENTITY_EMAIL_MATCH", "repo": None,
                                            "message": "Resume email appears in the GitHub commit history."})

    for r in res["repos"]:
        finalize_repo(r)
        for p in r["positives"]:
            res["verified_signals"].append({"id": "POSITIVE", "repo": r["full_name"], "message": p})
    if res["skills"]["confirmed"]:
        res["verified_signals"].append({"id": "SKILLS_CONFIRMED", "repo": None,
                                        "message": "Languages confirmed on GitHub: " + ", ".join(res["skills"]["confirmed"])})

    return finish(res["status"] or "analyzed")

def _aggregate(res, pflags):
    repos = res["repos"]
    flags = list(pflags)
    for r in repos:
        flags.extend(r["flags"])
        r.pop("_readme", None)
    res["flags"] = flags

    if repos:
        w_total = sum((2 if r["claimed"] else 1) for r in repos)
        mean = sum(r["score"] * (2 if r["claimed"] else 1) for r in repos) / w_total
        ppen = min(PROFILE_PENALTY_CAP, sum(SEV_PENALTY_PROFILE[f["severity"]] for f in pflags))
        res["github_score"] = int(round(max(0, min(100, mean - ppen))))
    else:
        res["github_score"] = None

    sev = [f["severity"] for f in flags]
    low_count = sum(1 for f in flags if f["severity"] == "low")
    if "high" in sev:
        res["risk_level"] = "high"
    elif "medium" in sev or low_count >= 3:
        res["risk_level"] = "review"
    elif res["status"] in ("analyzed", "partial"):
        res["risk_level"] = "low"
    else:
        res["risk_level"] = "review" if res["status"] == "not_found" else None

    for r in repos:
        for k in [k for k in r if k.startswith("_")]:
            r.pop(k)
        for k in [k for k in r["metrics"] if k.startswith("_")]:
            r["metrics"].pop(k)
    return res


_GENERIC_EVIDENCE = {"SINGLE_COMMIT_DUMP", "BACKDATED_COMMITS", "TIMELINE_MISMATCH", "COPIED_REPO_INDICATORS",
                     "ACCOUNT_YOUNGER_THAN_CLAIM", "SKILL_LANGUAGE_MISMATCH"}

def _repo_label(full, username):
    if not full:
        return None
    owner, _, name = full.partition("/")
    return name if owner.lower() == (username or "").lower() else full

def _compact(result, keep_info=False, include_repos=True):
    user = result.get("username")
    flags = []
    for f in result.get("flags") or []:
        if f["severity"] == "info" and not keep_info:
            continue
        item = {"id": f["id"], "severity": f["severity"], "message": f["message"]}
        label = _repo_label(f.get("repo"), user)
        if label:
            item["repo"] = label
        if f.get("evidence") and f["id"] not in _GENERIC_EVIDENCE:
            item["evidence"] = f["evidence"]
        flags.append(item)

    signals = []
    for s in result.get("verified_signals") or []:
        label = _repo_label(s.get("repo"), user)
        signals.append(s["message"] + (f" [{label}]" if label else ""))

    repos = []
    for r in result.get("repos") or []:
        m = r.get("metrics") or {}
        repos.append({"name": _repo_label(r["full_name"], user), "score": r["score"], "is_fork": r["is_fork"],
                      "claimed": r["claimed"], "commits": m.get("total_commits", 0),
                      "own_commits": m.get("own_commits_est", 0)})

    skills = result.get("skills") or {}
    return {
        "status": result.get("status"),
        "username": user,
        "profile_url": result.get("profile_url"),
        "github_score": result.get("github_score"),
        "risk_level": result.get("risk_level"),
        "repo_count": len(repos),
        "flags": flags,
        "verified_signals": signals,
        "repos": repos if include_repos else [],
        "skills": {"confirmed": skills.get("confirmed", []), "unconfirmed": skills.get("unconfirmed", [])},
        "warnings": result.get("warnings") or [],
    }

def analyze_github(extracted_data, resume_name=None, resume_email=None, claimed_years=None,
                   token=None, llm_fn=None, max_repos=4, max_api_calls=None, client=None, now=None,
                   keep_info=False, include_repos=True):
    full = _analyze_github_full(extracted_data, resume_name=resume_name, resume_email=resume_email,
                                claimed_years=claimed_years, token=token, llm_fn=llm_fn, max_repos=max_repos,
                                max_api_calls=max_api_calls, client=client, now=now)
    return _compact(full, keep_info=keep_info, include_repos=include_repos)

def report_lines(result):
    st = result["status"]
    if st == "not_provided":
        return ["GitHub: no link provided, so no code verification was possible (not penalised)."]
    if st == "not_found":
        return [f"GitHub: profile '{result['username']}' does not exist; confirm the link with the candidate."]
    lines = []
    if result["github_score"] is not None:
        n_repos = result.get("repo_count", len(result["repos"]))
        lines.append(f"GitHub score {result['github_score']}/100, risk level: {result['risk_level']} "
                     f"({n_repos} repo(s) analysed{', partial' if st == 'partial' else ''}).")
    for f in sorted(result["flags"], key=lambda x: ["high", "medium", "low", "info"].index(x["severity"])):
        where = f" [{f['repo']}]" if f.get("repo") else ""
        lines.append(f"{f['severity'].upper()}: {f['message']}{where}")
    for v in result["verified_signals"]:
        if isinstance(v, str):
            lines.append("Positive: " + v)
        else:
            lines.append("Positive: " + v["message"] + (f" [{v['repo']}]" if v.get("repo") else ""))
    return lines