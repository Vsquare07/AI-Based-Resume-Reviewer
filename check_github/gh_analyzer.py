import base64
import os
import re
from datetime import datetime, timedelta, timezone
from .gh_config import (
    BACKDATE_GAP_DAYS, BACKDATE_MIN_COMMITS, BACKDATE_WINDOW_SECONDS,
    BURST_MIN_COMMITS, BURST_WINDOW_SECONDS,
    DUMP_MAX_COMMITS, DUMP_MIN_ADDITIONS, DUMP_MIN_FILES, DUMP_MIN_SIZE_KB,
    LARGE_INITIAL_ADDITIONS, LOW_SHARE, STRUCTURAL, SUPPORTING, TIMELINE_SLACK_DAYS,
)
from .gh_helpers import _flag, _parse_dt, _norm, _words, scan_injection
from .gh_client import (
    GitHubError, NotFound, EmptyRepo, RateLimited, BudgetExceeded, _count,
)
_GENERIC_MSG = {"update", "updates", "commit", "initial commit", "first commit", "fix", "fixes", "changes",
                "test", "final", "done", "wip", ".", "add files", "upload files", "added files", "files",
                "code", "update readme.md", "update readme", "create readme.md", "initial", "minor changes"}

def _is_own(commit, ctx):
    login = ctx["login_l"]
    a = commit.get("author") or {}
    if (a.get("login") or "").lower() == login:
        return True
    ca = (commit.get("commit") or {}).get("author") or {}
    email = (ca.get("email") or "").lower()
    if email and email in ctx["own_emails"]:
        return True
    if re.match(rf"^(?:\d+\+)?{re.escape(login)}@users\.noreply\.github\.com$", email):
        return True
    name = _norm(ca.get("name") or "")
    return bool(name and name in ctx["own_names"])

def analyze_sample(sample, ctx):
    n = len(sample)
    own = sum(1 for c in sample if _is_own(c, ctx))
    foreign = sum(1 for c in sample
                  if ((c.get("author") or {}).get("login") or "").lower() not in ("", ctx["login_l"]))
    emails = set()
    msgs = []
    old, committer_times = [], []
    for c in sample:
        cm = c.get("commit") or {}
        ca, cc = cm.get("author") or {}, cm.get("committer") or {}
        e = (ca.get("email") or "").lower()
        if e and "noreply" not in e:
            emails.add(e)
        msgs.append(((cm.get("message") or "").split("\n")[0]).strip())
        ad, cd = _parse_dt(ca.get("date")), _parse_dt(cc.get("date"))
        if cd:
            committer_times.append(cd)
        if ad and cd and (cd - ad).total_seconds() / 86400 > BACKDATE_GAP_DAYS:
            old.append(cd)

    backdated = None
    if len(old) >= BACKDATE_MIN_COMMITS:
        span = (max(old) - min(old)).total_seconds()
        if span <= BACKDATE_WINDOW_SECONDS:
            backdated = {"commits": len(old), "recorded_within_minutes": round(span / 60)}

    burst = None
    ts = sorted(committer_times)
    j = 0
    best = 0
    for i in range(len(ts)):
        while (ts[i] - ts[j]).total_seconds() > BURST_WINDOW_SECONDS:
            j += 1
        best = max(best, i - j + 1)
    if best >= BURST_MIN_COMMITS:
        burst = {"commits": best, "window_minutes": BURST_WINDOW_SECONDS // 60}

    generic = sum(1 for m in msgs if m.lower() in _GENERIC_MSG or len(m) <= 2)
    generic_ratio = generic / len(msgs) if msgs else 0.0
    return {"n": n, "own": own, "foreign": foreign, "emails": emails, "messages": msgs,
            "backdated": backdated, "burst": burst, "generic_ratio": generic_ratio}


_VENDOR_SEGMENTS = {"node_modules", "venv", ".venv", "env", "vendor", "__pycache__", "dist", "build", "site-packages"}
_CODE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".c", ".h", ".cpp", ".cc", ".hpp", ".cs", ".go",
             ".rs", ".rb", ".php", ".swift", ".scala", ".dart", ".lua", ".sol", ".v", ".sv", ".vhd", ".ipynb",
             ".m", ".r", ".sh", ".sql", ".html", ".css", ".vue", ".svelte"}
_TEST_RE = re.compile(r"(^|/)(tests?|__tests__|specs?)/|(^|/)test_[^/]+\.py$|_test\.(py|go|rb|js|ts)$|"
                      r"\.(test|spec)\.(js|jsx|ts|tsx)$|(^|/)[^/]*tests?\.(java|kt|cs)$")
_MANIFESTS = {"requirements.txt", "pyproject.toml", "package.json", "pom.xml", "build.gradle", "cargo.toml",
              "go.mod", "gemfile", "composer.json", "setup.py", "cmakelists.txt", "makefile", "dockerfile",
              "docker-compose.yml", "docker-compose.yaml"}
_BOILERPLATE = {
    "create-react-app": ["src/reportwebvitals.js", "src/logo.svg", "public/logo192.png",
                         "src/setuptests.js", "src/app.test.js"],
    "vite-react": ["src/assets/react.svg", "public/vite.svg"],
    "create-next-app": ["public/next.svg", "public/vercel.svg"],
}
_DEFAULT_README_RE = re.compile(
    r"bootstrapped with \[?create react app|getting started with create react app|"
    r"this is a \[?next\.js\]?.{0,40}project bootstrapped|this template provides a minimal setup to get react working in vite|"
    r"available scripts\s*in the project directory", re.I | re.S)


def analyze_tree(paths):
    low = [p.lower() for p in paths]

    def vendored(p):
        return any(seg in _VENDOR_SEGMENTS for seg in p.split("/")[:-1])

    own = [p for p in low if not vendored(p)]
    ci = any(p.startswith(".github/workflows/") or p in (".gitlab-ci.yml", ".travis.yml", "jenkinsfile")
             or p.startswith(".circleci/") for p in own)
    tests = any(_TEST_RE.search(p) for p in own)
    manifest = any(p.split("/")[-1] in _MANIFESTS for p in own)
    license_file = next((p for p in own if re.match(r"^licen[sc]e(\.md|\.txt)?$", p)), None)
    source_files = sum(1 for p in own if os.path.splitext(p)[1] in _CODE_EXT)
    boiler = None
    for kit, markers in _BOILERPLATE.items():
        hits = sum(any(p == m or p.endswith("/" + m) for p in low) for m in markers)
        if hits >= 2:
            boiler = kit
            break
    deps = any(p.startswith(("node_modules/", "venv/", ".venv/")) for p in low)
    env_file = any(p == ".env" or p.endswith("/.env") for p in low)
    return {"ci": ci, "tests": tests, "manifest": manifest, "license_file": license_file,
            "source_files": source_files, "boilerplate": boiler, "committed_deps": deps, "env_file": env_file}

def readme_points(text):
    if not text:
        return 0, False
    stock = bool(_DEFAULT_README_RE.search(text))
    n = len(text)
    pts = 6 if n >= 1500 else 4 if n >= 600 else 2 if n >= 200 else 0
    headings = len(re.findall(r"^#{1,4}\s+\S", text, re.M))
    pts += 3 if headings >= 3 else 1 if headings >= 1 else 0
    pts += 2 if "```" in text else 0
    pts += 2 if re.search(r"\b(install|usage|getting started|how to run|setup|run the)\b", text, re.I) else 0
    pts += 1 if re.search(r"!\[|screenshot|demo|\.gif|\.png", text, re.I) else 0
    if stock:
        pts = min(pts, 2)
    return pts, stock

def _license_holder(content):
    m = re.search(r"copyright\s*(?:\(c\)|©)?\s*(?:\d{4}(?:\s*[-–,]\s*\d{4})*)?\s+([^\n]+)", content or "", re.I)
    if not m:
        return None
    holder = re.sub(r"all rights reserved\.?", "", m.group(1), flags=re.I).strip(" .,")
    if not holder or re.search(r"yyyy|fullname|your name|copyright owner|holders?>|\[.*\]|<.*>", holder, re.I):
        return None
    return holder

def analyze_repo(client, repo, ctx, claims):
    owner = (repo.get("owner") or {}).get("login") or ctx["login"]
    name = repo["name"]
    full = f"{owner}/{name}"
    base = f"/repos/{owner}/{name}"
    is_fork = bool(repo.get("fork"))
    foreign_owner = owner.lower() != ctx["login_l"]
    r = {
        "name": name, "full_name": full, "owner": owner,
        "url": repo.get("html_url") or f"https://github.com/{full}",
        "is_fork": is_fork, "claimed": bool(claims), "claims": [c["text"] for c in claims],
        "claim_kinds": sorted({c["kind"] for c in claims}),
        "metrics": {}, "flags": [], "positives": [], "components": {}, "warnings": [],
        "llm": None, "cap": None, "score": None, "quality_score": None,
        "_readme": "", "_paths": [], "_untrusted": [],
    }
    flags, m = r["flags"], r["metrics"]

    def add(fid, msg, evidence=None, severity=None, commit=None, url=None):
        flags.append(_flag(fid, msg, "repo", full, evidence, severity, commit=commit, url=url))

    def safe(fn, default, label):
        try:
            return fn()
        except (RateLimited, BudgetExceeded):
            raise
        except GitHubError as e:
            r["warnings"].append(f"{label}: {e}")
            return default

    try:
        total, newest = _count(client, f"{base}/commits")
    except EmptyRepo:
        total, newest = 0, []
    except NotFound:
        r["warnings"].append("repository not accessible")
        total, newest = 0, []
    m["total_commits"] = total

    first = None
    if total > 1:
        first_list = safe(lambda: client.get(f"{base}/commits", {"per_page": 1, "page": total})[0], [], "oldest commit")
        first = first_list[0] if first_list else None
    elif newest:
        first = newest[0]

    first_detail = {}
    if first and first.get("sha"):
        first_detail = safe(lambda: client.get(f"{base}/commits/{first['sha']}")[0], {}, "first commit detail")
    stats = (first_detail or {}).get("stats") or {}
    m["first_commit_additions"] = stats.get("additions", 0)
    m["first_commit_files"] = len((first_detail or {}).get("files") or [])
    first_sha = (first_detail or {}).get("sha") or (first or {}).get("sha")
    repo_url = repo.get("html_url") or f"https://github.com/{full}"
    first_url = (first_detail or {}).get("html_url") or (first or {}).get("html_url") or (f"{repo_url}/commit/{first_sha}" if first_sha else None)
    m["first_commit_sha"] = first_sha
    m["first_commit_url"] = first_url

    own_total = 0
    if total:
        own_total = safe(lambda: _count(client, f"{base}/commits", {"author": ctx["login"]})[0], 0, "own commit count")
    sample = safe(lambda: client.get(f"{base}/commits", {"per_page": 100})[0], [], "commit sample") if total else []
    s = analyze_sample(sample, ctx)
    m["sample_size"] = s["n"]

    first_dt = _parse_dt(((first or {}).get("commit") or {}).get("author", {}).get("date"))
    last_dt = _parse_dt(((newest[0] if newest else {}).get("commit") or {}).get("author", {}).get("date"))
    m["first_commit_date"] = first_dt.isoformat() if first_dt else None
    m["last_commit_date"] = last_dt.isoformat() if last_dt else None
    m["lifespan_days"] = (last_dt - first_dt).days if first_dt and last_dt else 0

    sample_frac = (s["own"] / s["n"]) if s["n"] else 0.0
    own_est = max(own_total, round(sample_frac * total)) if total else 0
    m["own_commits_est"] = own_est
    m["own_share"] = round(own_est / total, 2) if total else 0.0
    m["author_emails"] = sorted(s["emails"])

    paths = []
    tree_info = {}
    if total:
        branch = repo.get("default_branch") or "HEAD"
        tdata = safe(lambda: client.get(f"/repos/{owner}/{name}/git/trees/{branch}", {"recursive": 1})[0], {}, "file tree")
        paths = [t["path"] for t in (tdata or {}).get("tree", []) if t.get("type") == "blob"]
        if (tdata or {}).get("truncated"):
            r["warnings"].append("file tree truncated (very large repo)")
        tree_info = analyze_tree(paths)
    r["_paths"] = paths
    m.update({k: tree_info.get(k) for k in ("ci", "tests", "manifest", "source_files", "boilerplate")})

    readme_text = ""
    try:
        rd = client.get(f"{base}/readme")[0]
        readme_text = base64.b64decode(rd.get("content") or "").decode("utf-8", errors="ignore")
    except NotFound:
        pass
    except (RateLimited, BudgetExceeded):
        raise
    except GitHubError as e:
        r["warnings"].append(f"readme: {e}")
    r["_readme"] = readme_text
    m["readme_chars"] = len(readme_text)

    langs = safe(lambda: client.get(f"{base}/languages")[0], {}, "languages") if total else {}
    m["languages"] = langs or {}

    prs = safe(lambda: _count(client, f"{base}/pulls", {"state": "all"})[0], 0, "pull requests") if total else 0
    m["pull_requests"] = prs
    m["stars"] = repo.get("stargazers_count", 0)
    m["size_kb"] = repo.get("size", 0)

    license_holder = None
    if tree_info.get("license_file") and not is_fork:
        ld = safe(lambda: client.get(f"{base}/license")[0], {}, "license")
        try:
            license_holder = _license_holder(base64.b64decode((ld or {}).get("content") or "").decode("utf-8", "ignore"))
        except Exception:
            license_holder = None

    r["_untrusted"] = [("README", readme_text), ("repo description", repo.get("description") or ""),
                       ("commit messages", "\n".join(s["messages"]))] + \
                      [("resume claim", c["text"]) for c in claims]

    for src, text in r["_untrusted"]:
        hit = scan_injection(text)
        if hit:
            add("PROMPT_INJECTION_ATTEMPT", f"Text aimed at an AI scorer found in {src}.", evidence=hit)
            break

    if is_fork and own_est == 0:
        add("FORK_NO_CONTRIBUTION", "Claimed repo is a fork and the candidate has no commits in it.")
    elif foreign_owner and not is_fork and own_est == 0:
        add("LINKED_REPO_NO_CONTRIBUTION", f"Resume links {full}, owned by someone else, with no commits by the candidate.")
    elif (is_fork or foreign_owner) and own_est > 0:
        r["positives"].append(f"{own_est} commit(s) by the candidate in {full}")

    if not is_fork and not foreign_owner and total >= 3 and own_est == 0 and s["n"] >= 3:
        add("ZERO_OWN_COMMITS", "No commits in this repo can be attributed to the candidate.",
            evidence=f"{s['foreign']} of {s['n']} sampled commits belong to other GitHub accounts")
    elif not is_fork and not foreign_owner and total >= 10 and 0 < own_est and m["own_share"] < LOW_SHARE:
        add("LOW_OWN_COMMIT_SHARE", f"Candidate wrote about {int(m['own_share'] * 100)}% of the commits.")

    if not is_fork:
        if total and total <= DUMP_MAX_COMMITS and (
                m["first_commit_additions"] >= DUMP_MIN_ADDITIONS or m["first_commit_files"] >= DUMP_MIN_FILES
                or m["size_kb"] >= DUMP_MIN_SIZE_KB):
            commit_part = f" (commit {first_sha[:7]})" if first_sha else ""
            link_part = f": {first_url}" if first_url else "."
            add("SINGLE_COMMIT_DUMP",
                f"{total} commit(s) carrying {m['first_commit_additions']} added lines / {m['first_commit_files']} files{commit_part}{link_part}",
                evidence="Benign cause: an old project uploaded in one go. Treat as a prompt for a question, not proof.",
                commit=first_sha, url=first_url)
        elif total > DUMP_MAX_COMMITS and m["first_commit_additions"] >= LARGE_INITIAL_ADDITIONS:
            commit_part = f" (commit {first_sha[:7]})" if first_sha else ""
            link_part = f": {first_url}" if first_url else "."
            add("LARGE_INITIAL_COMMIT",
                f"First commit adds {m['first_commit_additions']} lines (imported or scaffolded){commit_part}{link_part}",
                commit=first_sha, url=first_url)
        if s["backdated"]:
            add("BACKDATED_COMMITS",
                f"{s['backdated']['commits']} commits were authored 90+ days before being recorded, all within "
                f"{s['backdated']['recorded_within_minutes']} minutes.",
                evidence="Benign causes: repository migration or history rewrite.")
        if s["burst"]:
            add("BURST_COMMITS", f"{s['burst']['commits']} commits recorded within {s['burst']['window_minutes']} minutes.")
        if license_holder:
            holder_norm = _norm(license_holder)
            generic = re.search(r"contributors|authors|developers", license_holder, re.I)
            related = any(len(t) >= 3 and t in holder_norm for t in ctx["own_name_norms"]) or \
                      any(holder_norm == n or (len(holder_norm) >= 3 and holder_norm in n) for n in ctx["own_name_norms"])
            if not generic and not related:
                add("LICENSE_HOLDER_MISMATCH", f"LICENSE copyright holder is '{license_holder}', unrelated to the candidate.")

    if not readme_text:
        add("NO_README", "Repository has no README.")
    rpts, stock = readme_points(readme_text)
    if stock:
        add("DEFAULT_README", "README is the stock starter-template text.")
    if tree_info.get("boilerplate"):
        add("BOILERPLATE_FILES", f"Default {tree_info['boilerplate']} starter files are still present.")
    if tree_info.get("committed_deps"):
        add("COMMITTED_DEPENDENCIES", "node_modules / venv is committed to the repo.")
    if tree_info.get("env_file"):
        add("ENV_FILE_COMMITTED", "A .env file is committed (possible secrets).")

    for c in claims:
        years = [int(y) for y in re.findall(r"\b((?:19|20)\d{2})\b", c["text"])]
        if years and first_dt and not re.search(r"\b(present|current|ongoing|now|till date)\b", c["text"], re.I):
            limit = datetime(max(years), 12, 31, tzinfo=timezone.utc) + timedelta(days=TIMELINE_SLACK_DAYS)
            if first_dt > limit:
                add("TIMELINE_MISMATCH",
                    f"Resume dates this project to {max(years)} but the repo's history starts {first_dt.date()}.",
                    evidence="Benign cause: an older project uploaded later.")
                break

    ids = {f["id"] for f in flags}
    structural, supporting = ids & STRUCTURAL, ids & SUPPORTING
    if structural and len(structural | supporting) >= 2:
        sev = "high" if ("ZERO_OWN_COMMITS" in ids or len(structural | supporting) >= 3) else "medium"
        add("COPIED_REPO_INDICATORS",
            "Multiple independent signals suggest this repo may not be the candidate's own incremental work: "
            + ", ".join(sorted(structural | supporting)) + ".",
            evidence="Advisory: ask the candidate to walk through the code.", severity=sev)

    if tree_info.get("ci"):
        r["positives"].append("CI workflow present")
    if tree_info.get("tests"):
        r["positives"].append("automated tests present")
    if prs:
        r["positives"].append(f"{prs} pull request(s) (PR workflow)")

    m["_readme_points_det"] = rpts
    m["_license_holder"] = license_holder
    m["_generic_ratio"] = s["generic_ratio"]
    m["_total_for_quality"] = own_est if (is_fork or foreign_owner) else total
    return r