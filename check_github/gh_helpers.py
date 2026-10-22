import re
from datetime import datetime
from .gh_config import FLAG_CATALOG

def _flag(fid, message, scope="repo", repo=None, evidence=None, severity=None):
    return {
        "id": fid,
        "severity": severity or FLAG_CATALOG[fid][0],
        "scope": scope,
        "repo": repo,
        "message": message,
        "evidence": evidence,
    }

def _parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None

def _norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())

def _words(s):
    return re.findall(r"[a-z0-9]+", (s or "").lower())

def _alnum_join(s):
    return " ".join(_words(s))

def _walk(obj, field=None):
    if isinstance(obj, str):
        yield field, obj
    elif isinstance(obj, (list, tuple, set)):
        for item in obj:
            yield from _walk(item, field)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk(v, field if field else k)

def _sanitize(text, limit):
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text or "")
    text = text.replace("<<<", "< < <").replace(">>>", "> > >")
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text[:limit]

_INJECTION_PATTERNS = [
    r"ignore (?:all |any |the |your )?(?:previous|prior|above|earlier) (?:instructions?|prompts?|rules?)",
    r"disregard (?:all |any |the |your )?(?:previous|prior|above|earlier) (?:instructions?|prompts?|rules?)",
    r"(?:give|assign|award|rate|score) (?:this|the) (?:candidate|resume|applicant|profile|developer) .{0,40}(?:100|perfect|maximum|highest|top score|10/10)",
    r"do not (?:flag|report|penali[sz]e|mention) (?:this|any|the) (?:repo|repository|candidate|resume|fraud|issue)",
    r"(?:reveal|print|show|repeat|output) (?:your|the) (?:system|developer) (?:prompt|message|instructions?)",
    r"\bfraud_?(?:detected|suspected)\b[\"']?\s*[:=]\s*false",
    r"\b(?:hire|select|shortlist) (?:this|the) (?:candidate|applicant)\b|\bhire me\b",
]
_INJECTION_RE = [re.compile(p, re.I) for p in _INJECTION_PATTERNS]

def scan_injection(text):
    if not text:
        return None
    for rx in _INJECTION_RE:
        m = rx.search(text)
        if m:
            return m.group(0)[:120]
    return None