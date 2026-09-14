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

SECTIONS = [{"id": "sec-1", "name": "Staging"}]
COLLECTIONS = [{"id": "col-1", "sectionId": "sec-1", "title": "Getting Started"}]

# --- create conflict recovery (main's slug lookup + PATCH) still works -------
def conflict_routes(method, url, n):
    if "/sections" in url:
        return FakeResponse(200, SECTIONS)
    if "/collections" in url:
        return FakeResponse(200, COLLECTIONS)
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
        FERNDESK_TARGET="staging",
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
        "getting-started-quickstart", {}).get("id") == "art-9", cache_path.read_text())
    check("conflict recovery is logged", any("recovered-update" in line for line in logs), logs)
finally:
    restore(saved)

# --- end-to-end: a permanently rate-limited page fails the run honestly -----
def sync_routes(method, url, n):
    if "/sections" in url:
        return FakeResponse(200, SECTIONS)
    if "/collections" in url:
        return FakeResponse(200, COLLECTIONS)
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
        FERNDESK_TARGET="staging",
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
    check("no article id cached for a failed write", json.loads(cache_path.read_text()) == {}, cache_path.read_text())
    check("FAILURES line is logged", any(line.startswith("FAILURES ") for line in logs), logs)
finally:
    restore(saved)

if failures:
    print(f"ferndesk-sync-retry: {len(failures)} check(s) failed", file=sys.stderr)
    sys.exit(1)
print("ferndesk-sync-retry: ok")
