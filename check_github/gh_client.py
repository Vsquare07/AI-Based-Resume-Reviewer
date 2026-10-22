import os
import re
import time
import requests
from .gh_config import API

class GitHubError(Exception):
    pass
class NotFound(GitHubError):
    pass
class EmptyRepo(GitHubError):
    pass
class RateLimited(GitHubError):
    def __init__(self, msg, reset=None):
        super().__init__(msg)
        self.reset = reset
class BudgetExceeded(GitHubError):
    pass
class GitHubClient:
    def __init__(self, token=None, max_calls=60, timeout=10):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.max_calls = max_calls
        self.calls = 0
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "resume-screener-github-check",
        })
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"

    @property
    def authenticated(self):
        return bool(self.token)

    def get(self, path, params=None):
        last_err = None
        r = None
        for attempt in range(3):
            if self.calls >= self.max_calls:
                raise BudgetExceeded(f"API call budget of {self.max_calls} reached")
            self.calls += 1
            try:
                r = self.session.get(API + path, params=params, timeout=self.timeout)
            except requests.RequestException as e:
                last_err = e
                time.sleep(0.5 * (2 ** attempt))
                continue
            if r.status_code >= 500:
                last_err = GitHubError(f"http {r.status_code}")
                time.sleep(0.5 * (2 ** attempt))
                continue
            break
        else:
            raise GitHubError(f"network error: {last_err}")

        sc = r.status_code
        if sc == 200:
            return r.json(), r.headers
        if sc == 404:
            raise NotFound(path)
        if sc == 409:
            raise EmptyRepo(path)
        if sc in (403, 429):
            limited = (r.headers.get("X-RateLimit-Remaining") == "0" or sc == 429
                       or r.headers.get("Retry-After") or "rate limit" in r.text.lower())
            if limited:
                raise RateLimited("GitHub rate limit hit", reset=r.headers.get("X-RateLimit-Reset"))
            raise GitHubError("forbidden")
        if sc == 451:
            raise GitHubError("unavailable for legal reasons")
        if sc == 422:
            raise GitHubError("unprocessable request")
        raise GitHubError(f"http {sc}")

def _last_page(headers):
    link = ""
    try:
        link = headers.get("Link") or headers.get("link") or ""
    except AttributeError:
        pass
    m = re.search(r'[?&]page=(\d+)[^>]*>\s*;\s*rel="last"', link)
    return int(m.group(1)) if m else None

def _count(client, path, params=None):
    p = dict(params or {})
    p["per_page"] = 1
    data, headers = client.get(path, p)
    last = _last_page(headers)
    total = last if last else (len(data) if isinstance(data, list) else 0)
    return total, data