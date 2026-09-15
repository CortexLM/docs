#!/usr/bin/env python3
"""Guards the FernDesk sync write-path retry policy (COR-444 residual).

`POST /articles` answers 429 `rate_limited` under load, so the write path has to
back off, honour `Retry-After`, and stay bounded. Runs offline: the HTTP client
is faked and `time.sleep` is virtual, so no network and no real waits.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "ferndesk_sync", ROOT / "scripts" / "ferndesk_sync.py"
)
fs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fs)

failures: list[str] = []


def check(name: str, cond: bool, detail: object = "") -> None:
    if cond:
        print(f"ok   {name}")
    else:
        failures.append(name)
        print(f"FAIL {name} {detail}")


@contextmanager
def env(**pairs: str):
    saved = {k: os.environ.get(k) for k in pairs}
    os.environ.update({k: str(v) for k, v in pairs.items()})
    try:
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class FakeTime:
    """Virtual clock: `sleep` advances `monotonic` so deadlines are testable."""

    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds

    def monotonic(self) -> float:
        return self.now


class FakeResponse:
    def __init__(self, status_code: int, payload: object = None, headers=None) -> None:
        self.status_code = status_code
        self.headers = headers or {}
        body = b"" if payload is None else json.dumps(payload).encode()
        self.content = body
        self.text = body.decode()


class FakeClient:
    """Scripted transport; records every request it is asked to make."""

    def __init__(self, script) -> None:
        self.script = script
        self.calls: list[tuple[str, str]] = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url))
        return self.script(method, url, len(self.calls))


def install(script, monkeypatch_time: bool = True):
    """Point the sync module at a fake transport and (optionally) a virtual clock."""
    client = FakeClient(script)
    logs: list[str] = []
    saved = (fs._http_client, fs.log, fs.time if monkeypatch_time else None)
    fake_time = FakeTime()
    fs._http_client = lambda: ("curl_cffi", client)
    fs.log = lambda msg: logs.append(str(msg))
    if monkeypatch_time:
        fs.time = fake_time
    return client, logs, fake_time, saved


def restore(saved) -> None:
    fs._http_client, fs.log, saved_time = saved
    if saved_time is not None:
        fs.time = saved_time
    fs._write_budget_spent = 0.0


# --- Retry-After parsing -----------------------------------------------------
check("retry-after absent is None", fs._retry_after_seconds(None) is None)
check("retry-after blank is None", fs._retry_after_seconds("   ") is None)
check("retry-after garbage is None", fs._retry_after_seconds("soon") is None)
check("retry-after seconds parsed", fs._retry_after_seconds("45") == 45.0)
check("retry-after negative clamps to 0", fs._retry_after_seconds("-3") == 0.0)
_date = fs.email.utils.formatdate(fs.time.time() + 120, usegmt=True)
_parsed = fs._retry_after_seconds(_date)
check(
    "retry-after HTTP-date parsed",
    _parsed is not None and 100 <= _parsed <= 130,
    _parsed,
)
check("header helper tolerates None", fs._header(None, "Retry-After") is None)
check("header helper rejects non-str", fs._header({"Retry-After": 5}, "Retry-After") is None)

# --- Delay ladder ------------------------------------------------------------
_wait, why = fs._retry_delay(0, None, 503)
check("first backoff is the base", _wait == fs._BACKOFF_BASE and why == "backoff", (_wait, why))
_wait, _ = fs._retry_delay(1, None, 503)
check("backoff grows exponentially", _wait == fs._BACKOFF_BASE * 2, _wait)
_wait, _ = fs._retry_delay(9, None, 503)
check("backoff is capped", _wait == fs._BACKOFF_CAP, _wait)
_wait, why = fs._retry_delay(0, None, 429)
check("429 uses the slower ladder", _wait == fs._RATE_LIMIT_BACKOFF_BASE, (_wait, why))
_wait, _ = fs._retry_delay(6, None, 429)
check("429 ladder reaches its higher cap", _wait == fs._RATE_LIMIT_BACKOFF_CAP, _wait)
_wait, why = fs._retry_delay(0, 45.0, 429)
check("retry-after wins when larger", _wait == 45.0 and why == "Retry-After", (_wait, why))
_wait, why = fs._retry_delay(0, 1.0, 429)
check("server floor never undercut", _wait == fs._RATE_LIMIT_BACKOFF_BASE, _wait)
_wait, why = fs._retry_delay(0, fs._RETRY_AFTER_CAP + 1, 429)
check("absurd retry-after falls back to backoff", _wait == fs._RATE_LIMIT_BACKOFF_BASE and "cap" in why, (_wait, why))

# --- 429 then success on the write path -------------------------------------
def flaky_then_ok(method, url, n):
    if n < 3:
        return FakeResponse(429, {"error": "Too many requests", "code": "rate_limited"},
                            {"Retry-After": "20"})
    return FakeResponse(201, {"id": "art-1", "status": "published"})


client, logs, fake_time, saved = install(flaky_then_ok)
try:
    with env(FERNDESK_WRITE_RETRIES="5", FERNDESK_WRITE_DEADLINE="600"):
        art = fs.api("k", "/articles", "POST", {"title": "t"}, label="getting-started-quickstart")
    check("write retries through 429 and succeeds", art.get("id") == "art-1", art)
    check("write made three attempts", len(client.calls) == 3, client.calls)
    check("retry-after honoured on every wait", fake_time.slept == [20.0, 20.0], fake_time.slept)
    check("write method is POST throughout", {m for m, _ in client.calls} == {"POST"}, client.calls)
    check("logs name the article slug", any("getting-started-quickstart" in line for line in logs), logs)
    check("logs report the rate limit", any("HTTP 429" in line for line in logs), logs)
    check("logs report the wait reason", any("Retry-After" in line for line in logs), logs)
finally:
    restore(saved)

# --- exhausted retries raise with the body ----------------------------------
client, logs, fake_time, saved = install(lambda m, u, n: FakeResponse(429, {"code": "rate_limited"}, {}))
try:
    with env(FERNDESK_WRITE_RETRIES="4"):
        raised = None
        try:
            fs.api("k", "/articles", "POST", {}, label="slug-x")
        except RuntimeError as e:
            raised = str(e)
    check("exhausted retries raise", raised is not None, raised)
    check("error keeps the last status", raised and "429" in raised, raised)
    check("error keeps the api code", raised and "rate_limited" in raised, raised)
    check("attempts match the configured budget", len(client.calls) == 4, len(client.calls))
finally:
    restore(saved)

# --- deadline stops the ladder ----------------------------------------------
client, logs, fake_time, saved = install(lambda m, u, n: FakeResponse(503, {"code": "unavailable"}, {}))
try:
    with env(FERNDESK_WRITE_RETRIES="20"):
        raised = None
        try:
            fs.api("k", "/articles", "POST", {}, deadline=10)
        except RuntimeError as e:
            raised = str(e)
    check("deadline aborts a long ladder", raised is not None and "deadline" in raised, raised)
    check("deadline stops before the cap", len(client.calls) == 3, len(client.calls))
    check("virtual clock stayed within the deadline", fake_time.now <= 10, fake_time.now)
finally:
    restore(saved)

# --- 5xx still retried, hard 4xx is not -------------------------------------
client, logs, fake_time, saved = install(
    lambda m, u, n: FakeResponse(400, {"error": "bad request", "code": "invalid_request"}, {})
)
try:
    with env(FERNDESK_WRITE_RETRIES="5"):
        raised = None
        try:
            fs.api("k", "/articles", "POST", {})
        except RuntimeError as e:
            raised = str(e)
    check("400 fails fast without retrying", len(client.calls) == 1, len(client.calls))
    check("400 surfaces its code", raised and "invalid_request" in raised, raised)
finally:
    restore(saved)

# --- reads keep the lighter budget ------------------------------------------
client, logs, fake_time, saved = install(lambda m, u, n: FakeResponse(429, {"code": "rate_limited"}, {}))
try:
    with env(FERNDESK_WRITE_RETRIES="99"):
        try:
            fs.api("k", "/articles")
        except RuntimeError:
            pass
    check("reads keep the shared default budget", len(client.calls) == fs._DEFAULT_RETRIES, len(client.calls))
finally:
    restore(saved)

# --- run-wide write budget --------------------------------------------------
client, logs, fake_time, saved = install(
    lambda m, u, n: FakeResponse(429, {"code": "rate_limited"}, {"Retry-After": "30"})
)
try:
    with env(FERNDESK_WRITE_RETRIES="50", FERNDESK_WRITE_BUDGET="100"):
        raised = None
        try:
            fs.api("k", "/articles", "POST", {}, label="budget-a")
        except RuntimeError as e:
            raised = str(e)
    check("run budget stops a rate-limit storm", raised is not None and "budget" in raised, raised)
    check("run budget spends no more than allowed", fake_time.now <= 100, fake_time.now)
    spent = fs._write_budget_spent
    check("run budget is charged for waits", 0 < spent <= 100, spent)
    check("run budget is shared across writes", spent > 0, spent)
finally:
    restore(saved)

# --- budget disabled means retry until the per-write deadline ----------------
client, logs, fake_time, saved = install(
    lambda m, u, n: FakeResponse(429, {"code": "rate_limited"}, {"Retry-After": "30"})
)
try:
    with env(FERNDESK_WRITE_RETRIES="50", FERNDESK_WRITE_BUDGET="0"):
        raised = None
        try:
            fs.api("k", "/articles", "POST", {}, deadline=120)
        except RuntimeError as e:
            raised = str(e)
    check("budget 0 disables the run-wide cap", raised is not None and "deadline" in raised, raised)
finally:
    restore(saved)

# --- shared fixtures for the end-to-end runs ---------------------------------
docs_root = Path(tempfile.mkdtemp(prefix="ferndesk-docs-"))
(docs_root / "getting-started").mkdir(parents=True)
(docs_root / "getting-started" / "quickstart.mdx").write_text(
    "---\ntitle: Quickstart\n---\n\nHello.\n", encoding="utf-8"
)

SECTIONS = [{"id": "sec-1", "name": "Production"}]
COLLECTIONS = [{"id": "col-1", "sectionId": "sec-1", "title": "Getting Started"}]

# --- slug lookup / create conflict recovery (lookup-before-create + PATCH) -------
def conflict_routes(method, url, n):
    if "/sections" in url:
        return FakeResponse(200, SECTIONS)
    if "/collections" in url:
        return FakeResponse(200, COLLECTIONS)
    if "/articles" in url and url.endswith("/publish") and method == "POST":
        return FakeResponse(200, {"id": "art-9", "status": "published"})
    if "/articles" in url and method == "POST":
        return FakeResponse(409, {"error": "slug already exists", "code": "conflict"})
    if "/articles" in url and "slug=" in url:
        return FakeResponse(200, {"results": [{"id": "art-9", "slug": "getting-started-quickstart",
                                               "status": "draft", "sectionId": "sec-1"}],
                                  "has_more": False})
    if "/articles" in url and method == "PATCH":
        return FakeResponse(200, {"id": "art-9", "status": "draft"})
    if "/articles" in url:
        return FakeResponse(200, {"results": [], "has_more": False})
    return FakeResponse(404, {"code": "not_found"})


summary_path = docs_root / "summary-conflict.json"
cache_path = docs_root / "cache-conflict.json"
client, logs, fake_time, saved = install(conflict_routes)
try:
    with env(
        FERNDESK_API_KEY="test-key",
        FERNDESK_TARGET="production",
        FERNDESK_SLUG_CACHE=str(cache_path),
        FERNDESK_SUMMARY_PATH=str(summary_path),
        DOCS_ROOT=str(docs_root),
        FERNDESK_FULL_SCAN="1",
    ):
        code = fs.main()
    summary = json.loads(summary_path.read_text())
    check("conflict recovery keeps the run green", code == 0, code)
    check("conflict recovery counts an update", summary.get("updated") == 1, summary)
    check("conflict recovery reports no failures", summary.get("failed") == 0, summary)
    check("conflict recovery caches the found id", json.loads(cache_path.read_text()).get(
        "by_slug", {}).get("getting-started-quickstart", {}).get("id") == "art-9",
        cache_path.read_text())
    check("conflict recovery is logged", any(("recovered-update" in line or "lookup-update" in line) for line in logs), logs)
finally:
    restore(saved)

# --- end-to-end: a permanently rate-limited page fails the run honestly -----
def sync_routes(method, url, n):
    if "/sections" in url:
        return FakeResponse(200, SECTIONS)
    if "/collections" in url:
        return FakeResponse(200, COLLECTIONS)
    if "/articles" in url and url.endswith("/publish") and method == "POST":
        return FakeResponse(200, {"id": "art-1", "status": "published"})
    if "/articles" in url and method == "POST":
        # The residual COR-444 case: article creation stays rate limited.
        return FakeResponse(429, {"error": "Too many requests", "code": "rate_limited"},
                            {"Retry-After": "5"})
    if "/articles" in url:
        # Slug scan lists the section before the write path runs.
        return FakeResponse(200, {"results": [], "has_more": False})
    return FakeResponse(404, {"code": "not_found"})


summary_path = docs_root / "summary.json"
cache_path = docs_root / "cache.json"
client, logs, fake_time, saved = install(sync_routes)
try:
    with env(
        FERNDESK_API_KEY="test-key",
        FERNDESK_TARGET="production",
        FERNDESK_WRITE_RETRIES="3",
        FERNDESK_SLUG_CACHE=str(cache_path),
        FERNDESK_SUMMARY_PATH=str(summary_path),
        DOCS_ROOT=str(docs_root),
        FERNDESK_FULL_SCAN="1",
    ):
        code = fs.main()
    summary = json.loads(summary_path.read_text())
    check("a stuck page fails the run", code == 1, code)
    check("summary counts the failure", summary.get("failed") == 1, summary)
    check("summary names the stuck slug", summary.get("failed_slugs") == ["getting-started-quickstart"], summary)
    check("summary still reports the page total", summary.get("pages") == 1, summary)
    check("no article id cached for a failed write",
          json.loads(cache_path.read_text()).get("by_slug") == {}, cache_path.read_text())
    check("FAILURES line is logged", any(line.startswith("FAILURES ") for line in logs), logs)
finally:
    restore(saved)

# --- production only: a staging target must be refused, not published --------
# docs.cortex.foundation serves the FernDesk Production section. A staging
# mirror put pre-prod articles on the public domain, so the sync refuses any
# target other than production rather than quietly creating one.
def never_called(method, url, n):
    raise AssertionError(f"staging target must not reach the API: {method} {url}")


summary_path = docs_root / "summary-staging.json"
client, logs, fake_time, saved = install(never_called)
try:
    with env(
        FERNDESK_API_KEY="test-key",
        FERNDESK_TARGET="staging",
        FERNDESK_SUMMARY_PATH=str(summary_path),
        DOCS_ROOT=str(docs_root),
    ):
        code = fs.main()
    check("a staging target is refused", code == 2, code)
    check("refusal names the target", any("staging" in line for line in logs), logs)
    check("refusal explains the public-domain reason",
          any("public" in line.lower() for line in logs), logs)
    check("no summary written for a refused run", not summary_path.exists(), summary_path)
finally:
    restore(saved)

# --- retire: unpublish articles whose MDX page is gone ----------------------
# Deleting an MDX page does not remove its FernDesk article; the upsert path
# never deletes. Without an explicit retire, a retired page keeps serving on
# the public domain (how /staging and duplicate hubs stayed reachable).
def retire_routes(method, url, n):
    if "/sections" in url:
        return FakeResponse(200, SECTIONS)
    if "/collections" in url:
        return FakeResponse(200, COLLECTIONS)
    if "/articles" in url and url.endswith("/unpublish") and method == "POST":
        retire_calls.append(url)
        return FakeResponse(200, {"id": "art-orphan", "status": "draft"})
    if "/articles" in url and url.endswith("/publish") and method == "POST":
        return FakeResponse(200, {"id": "art-1", "status": "published"})
    if "/articles" in url and method == "PATCH":
        return FakeResponse(200, {"id": "art-1", "status": "published"})
    if "/articles" in url and method == "POST":
        return FakeResponse(200, {"id": "art-1", "status": "published"})
    if "/articles" in url:
        return FakeResponse(200, {"results": [
            {"id": "art-1", "slug": "getting-started-quickstart", "status": "published",
             "sectionId": "sec-1", "keywords": "source:mintlify;path:getting-started/quickstart.mdx"},
            {"id": "art-orphan", "slug": "staging-index", "status": "published",
             "sectionId": "sec-1", "keywords": "source:mintlify;path:staging/index.mdx"},
            {"id": "art-fern", "slug": "fern-only", "status": "published",
             "sectionId": "sec-1", "keywords": "hand-written"},
        ], "has_more": False})
    return FakeResponse(404, {"code": "not_found"})


retire_calls: list = []
summary_path = docs_root / "summary-retire.json"
cache_path = docs_root / "cache-retire.json"
client, logs, fake_time, saved = install(retire_routes)
try:
    with env(
        FERNDESK_API_KEY="test-key",
        FERNDESK_TARGET="production",
        FERNDESK_RETIRE="1",
        FERNDESK_SLUG_CACHE=str(cache_path),
        FERNDESK_SUMMARY_PATH=str(summary_path),
        DOCS_ROOT=str(docs_root),
        FERNDESK_FULL_SCAN="1",
    ):
        code = fs.main()
    summary = json.loads(summary_path.read_text())
    check("retire keeps the run green", code == 0, code)
    check("retire unpublishes the orphaned page",
          any(u.endswith("/articles/art-orphan/unpublish") for u in retire_calls), retire_calls)
    check("retire leaves FernDesk-only articles alone",
          not any("art-fern" in u for u in retire_calls), retire_calls)
    check("retire counts what it unpublished", summary.get("retired") == 1, summary)
    check("retire is logged", any(line.startswith("retired ") for line in logs), logs)
finally:
    restore(saved)

# --- retire is off unless asked for -----------------------------------------
retire_calls = []
summary_path = docs_root / "summary-no-retire.json"
cache_path = docs_root / "cache-no-retire.json"
client, logs, fake_time, saved = install(retire_routes)
try:
    with env(
        FERNDESK_API_KEY="test-key",
        FERNDESK_TARGET="production",
        FERNDESK_SLUG_CACHE=str(cache_path),
        FERNDESK_SUMMARY_PATH=str(summary_path),
        DOCS_ROOT=str(docs_root),
        FERNDESK_FULL_SCAN="1",
    ):
        code = fs.main()
    summary = json.loads(summary_path.read_text())
    check("retire stays off by default", retire_calls == [], retire_calls)
    check("no retired count when retire is off", "retired" not in summary, summary)
finally:
    restore(saved)

# --- identity is the Mintlify path, not the slug ----------------------------
# FernDesk rewrites a slug it considers taken: `chat` is stored as `chat-8hul5`.
# A sync that resolves identity by slug therefore never finds its article after
# a cache loss and creates another copy — which is how the public site ended up
# with nine `index-*` articles. Identity must come from the `path:<rel>` marker
# in keywords, which survives the rewrite.
def rewritten_slug_routes(method, url, n):
    if "/sections" in url:
        return FakeResponse(200, SECTIONS)
    if "/collections" in url:
        return FakeResponse(200, COLLECTIONS)
    if "/articles" in url and url.endswith("/publish") and method == "POST":
        return FakeResponse(200, {"id": "art-chat", "status": "published"})
    if "/articles" in url and url.endswith("/unpublish") and method == "POST":
        rewrite_retire_calls.append(url)
        return FakeResponse(200, {"id": "art-dup", "status": "draft"})
    if "/articles" in url and method == "PATCH":
        return FakeResponse(200, {"id": "art-chat", "status": "published"})
    if "/articles" in url and method == "POST":
        # A create here would be the bug: the article already exists.
        rewrite_create_calls.append(url)
        return FakeResponse(200, {"id": "art-new", "slug": "getting-started-quickstart-9x1yz",
                                  "status": "published"})
    if "/articles" in url:
        # The section already holds the page under a rewritten slug, plus a
        # second copy made by an earlier cache-losing run.
        return FakeResponse(200, {"results": [
            {"id": "art-chat", "slug": "getting-started-quickstart-8hul5",
             "status": "published", "sectionId": "sec-1",
             "keywords": "source:mintlify;path:getting-started/quickstart.mdx;fp:abc"},
            {"id": "art-dup", "slug": "getting-started-quickstart-2zzq7",
             "status": "published", "sectionId": "sec-1",
             "keywords": "source:mintlify;path:getting-started/quickstart.mdx;fp:old"},
        ], "has_more": False})
    return FakeResponse(404, {"code": "not_found"})


rewrite_retire_calls: list = []
rewrite_create_calls: list = []
summary_path = docs_root / "summary-rewrite.json"
cache_path = docs_root / "cache-rewrite.json"
client, logs, fake_time, saved = install(rewritten_slug_routes)
try:
    with env(
        FERNDESK_API_KEY="test-key",
        FERNDESK_TARGET="production",
        FERNDESK_SLUG_CACHE=str(cache_path),
        FERNDESK_SUMMARY_PATH=str(summary_path),
        DOCS_ROOT=str(docs_root),
        FERNDESK_FULL_SCAN="1",
    ):
        code = fs.main()
    summary = json.loads(summary_path.read_text())
    check("a rewritten slug is still found by path", rewrite_create_calls == [], rewrite_create_calls)
    check("the run stays green", code == 0, code)
    check("the existing article is updated", summary.get("updated") == 1, summary)
    check("nothing is created", summary.get("created") == 0, summary)
    check("the duplicate copy is reported", summary.get("duplicates") == 1, summary)
    check("a duplicate is logged for the operator",
          any(line.startswith("DUPLICATES ") for line in logs), logs)
    cached = json.loads(cache_path.read_text())
    check("the cache records the rewritten slug",
          cached.get("by_path", {}).get("getting-started/quickstart.mdx", {}).get("id") == "art-chat",
          cached)
finally:
    restore(saved)

# --- retire removes the duplicate copies, not the canonical one -------------
rewrite_retire_calls = []
rewrite_create_calls = []
summary_path = docs_root / "summary-rewrite-retire.json"
cache_path = docs_root / "cache-rewrite-retire.json"
client, logs, fake_time, saved = install(rewritten_slug_routes)
try:
    with env(
        FERNDESK_API_KEY="test-key",
        FERNDESK_TARGET="production",
        FERNDESK_RETIRE="1",
        FERNDESK_SLUG_CACHE=str(cache_path),
        FERNDESK_SUMMARY_PATH=str(summary_path),
        DOCS_ROOT=str(docs_root),
        FERNDESK_FULL_SCAN="1",
    ):
        code = fs.main()
    summary = json.loads(summary_path.read_text())
    check("retire unpublishes the duplicate",
          any(u.endswith("/articles/art-dup/unpublish") for u in rewrite_retire_calls),
          rewrite_retire_calls)
    check("retire keeps the canonical article",
          not any(u.endswith("/articles/art-chat/unpublish") for u in rewrite_retire_calls),
          rewrite_retire_calls)
    check("retire counts the duplicate", summary.get("retired") == 1, summary)
finally:
    restore(saved)

if failures:
    print(f"ferndesk-sync-retry: {len(failures)} check(s) failed", file=sys.stderr)
    sys.exit(1)
print("ferndesk-sync-retry: ok")
