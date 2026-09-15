#!/usr/bin/env python3
"""Sync CortexLM/docs (Mintlify MDX) → the FernDesk help center.

**Production only.** `docs.cortex.foundation` is a public site, so this script
writes to the FernDesk **Production** section and publishes there. A staging
mirror is deliberately not supported: staging articles were reachable on the
public domain, which is exactly the leak this repo must not repeat. Anything
that is not ready to be public does not belong in this tree.

Env:
  FERNDESK_API_KEY   required (Bearer). Never print/log the value.
  FERNDESK_TARGET    must be `production` when set (default: production)
  FERNDESK_DRY_RUN   1 = plan only (still needs API unless FERNDESK_DRY_LOCAL=1)
  FERNDESK_DRY_LOCAL 1 = discover pages only, no API
  FERNDESK_FULL_SCAN 1 = rebuild slug cache by listing all articles
  FERNDESK_SLUG_CACHE path to slug→id cache (default .ferndesk-slug-cache.json)
  FERNDESK_WRITE_RETRIES  attempts per article/collection write (default 12)
  FERNDESK_WRITE_DEADLINE seconds of retrying allowed per write (default 1800)
  FERNDESK_WRITE_BUDGET   seconds of retry time for the whole run (default 5400)
  FERNDESK_RETIRE    1 = also unpublish articles that no longer exist here
  DOCS_ROOT          docs repo root (default: cwd)

Idempotent upsert by slug. Never deletes FernDesk-only articles unless
`FERNDESK_RETIRE=1` is set explicitly (see `scripts/FERNDESK.md`).
"""
from __future__ import annotations

import datetime
import email.utils
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.ferndesk.com/v1"

# The FernDesk section this repository publishes to. One section, one public
# site: there is no staging mirror to keep in sync.
SECTION_NAME = "Production"

FOLDER_TO_COLLECTION = {
    "getting-started": "Getting Started",
    "chat": "Chat",
    "code": "Code",
    "bot": "Bot",
    "cli": "Cli",
    "api": "Api",
    "security": "Security",
    "problems": "Problems",
    "changelog": "Changelog",
}

ROOT_FILE_COLLECTION = {
    "index.mdx": "Index",
    "changelog.mdx": "Changelog",
    "status.mdx": "Getting Started",
}

SKIP_NAMES = {"docs.json", "README.md", "AGENTS.md", "LICENSE", "custom.css"}


def log(msg: str) -> None:
    print(msg, flush=True)


# Chrome-like UA so CF sees a browser-ish client alongside TLS impersonation.
_CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
_ACCEPT = "application/json, text/plain, */*"


def _in_ci() -> bool:
    return os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true"


def _http_client():
    """Prefer curl_cffi Chrome TLS fingerprint; urllib only outside CI if missing."""
    try:
        from curl_cffi import requests as cffi_requests  # type: ignore

        return ("curl_cffi", cffi_requests)
    except ImportError:
        if _in_ci():
            raise RuntimeError(
                "curl_cffi is required in CI (Cloudflare Error 1010 bans GHA urllib TLS). "
                "Install with: pip install curl_cffi"
            ) from None
        return ("urllib", None)


def _is_cf_1010(status: int, body: str) -> bool:
    if status != 403:
        return False
    b = body.lower()
    return "1010" in b or "browser_signature_banned" in b or "error 1010" in b


# Transient failures worth retrying. 429 is the article-write rate limit
# (`{"code":"rate_limited"}`); 5xx are origin hiccups behind Cloudflare.
_RETRY_STATUSES = (429, 502, 503, 504)
_WRITE_METHODS = {"POST", "PATCH", "PUT", "DELETE"}
_BACKOFF_BASE = 3.0
_BACKOFF_CAP = 90.0
# 429 needs a longer cool-down than 5xx/CF 1010 — FernDesk rate limits recover
# slowly once the article writes start tripping them.
_RATE_LIMIT_BACKOFF_BASE = 5.0
_RATE_LIMIT_BACKOFF_CAP = 180.0
# A server-supplied Retry-After past this cap is treated as unusable and the
# exponential ladder is used instead — an unbounded header must not park CI.
_RETRY_AFTER_CAP = 300.0
# Attempts per request. Writes additionally carry a per-write deadline and a
# run-wide budget so a rate-limited run always finishes and reports.
_DEFAULT_RETRIES = 12
_DEFAULT_WRITE_RETRIES = 12


def _env_number(name: str, default: float, minimum: float = 0.0) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw)
    except ValueError:
        log(f"WARN {name}={raw!r} is not a number; using {default:g}")
        return default
    if value < minimum:
        log(f"WARN {name}={raw!r} below minimum {minimum:g}; using {minimum:g}")
        return minimum
    return value


def _header(headers, name: str) -> str | None:
    """Read a response header from curl_cffi/urllib without trusting either API."""
    if headers is None:
        return None
    try:
        value = headers.get(name)
    except Exception:
        return None
    return value if isinstance(value, str) else None


def _retry_after_seconds(value: str | None) -> float | None:
    """Retry-After as delta-seconds or HTTP-date; None when absent or malformed."""
    if not value or not value.strip():
        return None
    raw = value.strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        pass
    try:
        when = email.utils.parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=datetime.timezone.utc)
    return max(0.0, (when - datetime.datetime.now(datetime.timezone.utc)).total_seconds())


def _retry_delay(attempt: int, retry_after: float | None, status: int | None = None) -> tuple[float, str]:
    """Wait before the next attempt: server's Retry-After when usable, else backoff.

    429 gets the slower ladder main introduced (5s doubling to 180s); other
    transient statuses and CF 1010 keep the shorter one (3s doubling to 90s).
    """
    if status == 429:
        backoff = min(_RATE_LIMIT_BACKOFF_CAP, _RATE_LIMIT_BACKOFF_BASE * (2**attempt))
    else:
        backoff = min(_BACKOFF_CAP, _BACKOFF_BASE * (2**attempt))
    if retry_after is None:
        return backoff, "backoff"
    if retry_after > _RETRY_AFTER_CAP:
        return backoff, f"backoff (Retry-After {retry_after:.0f}s over {_RETRY_AFTER_CAP:.0f}s cap)"
    return max(backoff, retry_after), "Retry-After"


# Retry time spent on writes so far. A sustained 429 storm across ~100 pages
# could otherwise run past the job timeout and lose the SUMMARY entirely, so
# the run stops retrying once the budget is gone and reports what landed.
_write_budget_spent = 0.0


def _write_budget_left() -> float | None:
    """Seconds of write retry time left, or None when the budget is disabled."""
    limit = _env_number("FERNDESK_WRITE_BUDGET", 5400.0, 0.0)
    if limit <= 0:
        return None
    return max(0.0, limit - _write_budget_spent)


def api(
    key: str,
    path: str,
    method: str = "GET",
    body: dict | None = None,
    retries: int | None = None,
    deadline: float | None = None,
    label: str | None = None,
):
    headers = {
        "Authorization": f"Bearer {key}",
        "Accept": _ACCEPT,
        "User-Agent": _CHROME_UA,
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"

    client_kind, cffi_requests = _http_client()
    last = None
    url = API + path
    tag = f" [{label}]" if label else ""

    # Writes are the constrained path (POST /articles 429 `rate_limited`), so
    # they additionally get a wall-clock deadline and share a run-wide budget;
    # reads just get the attempt count.
    if retries is None:
        retries = int(
            _env_number("FERNDESK_WRITE_RETRIES", _DEFAULT_WRITE_RETRIES, 1.0)
            if method in _WRITE_METHODS
            else _DEFAULT_RETRIES
        )
    if deadline is None and method in _WRITE_METHODS:
        deadline = _env_number("FERNDESK_WRITE_DEADLINE", 1800.0, 1.0)
    started = time.monotonic()
    retry_after: float | None = None
    retry_status: int | None = None
    status_note = "transient failure"
    write = method in _WRITE_METHODS
    budget_left = _write_budget_left() if write else None

    for i in range(retries):
        if i:
            wait, why = _retry_delay(i - 1, retry_after, retry_status)
            if deadline is not None and time.monotonic() - started + wait > deadline:
                last = f"{last} (deadline {deadline:.0f}s exceeded after {i} attempts)"
                break
            if budget_left is not None:
                if wait > budget_left:
                    last = (
                        f"{last} (write retry budget exhausted after {i} attempts; "
                        "rerun the sync once the rate limit clears)"
                    )
                    break
                budget_left -= wait
                globals()["_write_budget_spent"] = _write_budget_spent + wait
            log(
                f"{method} {path}{tag} retry {i}/{retries - 1} "
                f"{status_note}; sleep {wait:.1f}s ({why})"
            )
            time.sleep(wait)
        try:
            if client_kind == "curl_cffi":
                resp = cffi_requests.request(
                    method,
                    url,
                    headers=headers,
                    data=data,
                    timeout=(15, 60),  # connect, read — avoid multi-minute hangs
                    impersonate="chrome",
                )
                txt = (resp.text or "")[:400]
                if resp.status_code >= 400:
                    last = f"{method} {path} -> {resp.status_code} {txt}"
                    if resp.status_code in _RETRY_STATUSES or _is_cf_1010(
                        resp.status_code, txt
                    ):
                        retry_after = _retry_after_seconds(_header(resp.headers, "Retry-After"))
                        retry_status = resp.status_code
                        status_note = (
                            "cf1010/403"
                            if _is_cf_1010(resp.status_code, txt)
                            else f"HTTP {resp.status_code}"
                        )
                        continue
                    raise RuntimeError(last)
                raw = resp.content or b""
                return json.loads(raw) if raw else {}

            # urllib fallback (local/dev only — GHA TLS fingerprint is banned by CF)
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=90) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            txt = e.read().decode("utf-8", "replace")[:400]
            last = f"{method} {path} -> {e.code} {txt}"
            if e.code in _RETRY_STATUSES or _is_cf_1010(e.code, txt):
                retry_after = _retry_after_seconds(_header(e.headers, "Retry-After"))
                retry_status = e.code
                status_note = "cf1010/403" if _is_cf_1010(e.code, txt) else f"HTTP {e.code}"
                continue
            raise RuntimeError(last) from e
        except urllib.error.URLError as e:
            last = f"{method} {path} -> URLError {e}"
            retry_after = None
            retry_status = None
            status_note = f"transport error ({e})"
            continue
        except RuntimeError:
            raise
        except Exception as e:
            last = f"{method} {path} -> {type(e).__name__} {e}"
            retry_after = None
            retry_status = None
            status_note = f"transport error ({e})"
            continue
    raise RuntimeError(last or "retries exhausted")


def list_all(key: str, path: str, max_pages: int = 100) -> list:
    """Paginate FernDesk list endpoints with anti-loop guards.

    FernDesk has been observed to return has_more/next_cursor forever on
    /collections (GHA ran 13k+ pages / ~278k rows). Guard with:
      - max_pages hard cap
      - repeated next_cursor detection
      - stop when a page adds no new item ids
    """
    out: list = []
    cursor = None
    page_n = 0
    seen_cursors: set[str] = set()
    seen_ids: set = set()
    while True:
        page_n += 1
        if page_n > max_pages:
            log(f"list_all {path} stop: max_pages={max_pages} so_far={len(out)}")
            break
        p = path
        if "limit=" not in path and "pageSize=" not in path:
            sep0 = "&" if "?" in p else "?"
            p = f"{p}{sep0}limit=100"
        if cursor:
            sep = "&" if "?" in p else "?"
            p = f"{p}{sep}cursor={urllib.parse.quote(cursor)}"
        log(f"list_all {path} page={page_n} so_far={len(out)}")
        page = api(key, p)
        if isinstance(page, list):
            log(f"list_all {path} done count={len(page)} (array)")
            return page
        batch = page.get("results") or page.get("items") or []
        new_ids = 0
        for item in batch:
            out.append(item)
            iid = item.get("id") if isinstance(item, dict) else None
            if iid is not None and iid not in seen_ids:
                seen_ids.add(iid)
                new_ids += 1
        if not page.get("has_more") or not page.get("next_cursor"):
            break
        nxt = str(page["next_cursor"])
        if nxt in seen_cursors:
            log(f"list_all {path} stop: repeated cursor so_far={len(out)}")
            break
        if batch and new_ids == 0:
            log(f"list_all {path} stop: no new ids so_far={len(out)}")
            break
        seen_cursors.add(nxt)
        cursor = nxt
        time.sleep(0.2)
    log(f"list_all {path} done count={len(out)}")
    return out


def strip_frontmatter(text: str) -> tuple[dict, str]:
    meta: dict = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            block = text[3:end].strip()
            body = text[end + 4 :].lstrip("\n")
            for line in block.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip("\"'")
            return meta, body
    return meta, text


def mdx_to_markdown(body: str) -> str:
    lines = [ln for ln in body.splitlines() if not ln.startswith("import ")]
    text = "\n".join(lines)
    text = re.sub(r"<[A-Z][A-Za-z0-9]*(\s[^>]*)?/>", "", text)
    text = re.sub(r"</?[A-Z][A-Za-z0-9]*(\s[^>]*)?>", "", text)
    return text.strip() + "\n"


def content_fingerprint(md: str) -> str:
    return hashlib.sha256(md.encode()).hexdigest()[:16]


# `path:<rel>` is the Mintlify page a FernDesk article came from. It is written
# into `keywords` on every create and update, and it is the only stable identity
# this sync has — see `index_articles`. Keywords are `;`-separated, so the value
# stops at the next `;` (or whitespace) and not just at the next space.
_PATH_KEYWORD = re.compile(r"path:([^;\s]+)")


def keyword_path(keywords: str | None) -> str | None:
    if not keywords:
        return None
    m = _PATH_KEYWORD.search(keywords)
    return m.group(1) if m else None


def article_entry(article: dict) -> dict:
    return {
        "id": article.get("id"),
        "status": article.get("status"),
        "keywords": article.get("keywords") or "",
        "slug": article.get("slug"),
    }


def index_articles(articles: list) -> tuple[dict, dict, list]:
    """Index FernDesk articles by slug, by Mintlify path, and collect duplicates.

    A slug is not a stable identity here. FernDesk rewrites a slug it considers
    taken — `chat` becomes `chat-8hul5` — so a run that loses its cache scans a
    set of hashed slugs, finds no match for `chat`, and creates the page again
    under a fresh hash. That is how the public site accumulated nine `index-*`
    articles and a second copy of every hub.

    The `path:<rel>` marker this script writes into `keywords` survives the
    rewrite, so it is what identity is resolved against. Articles sharing a path
    are copies of one page; the first is canonical and the rest are returned as
    duplicates for the retire pass.
    """
    by_slug: dict = {}
    by_path: dict = {}
    duplicates: list = []
    for article in articles:
        slug = article.get("slug")
        if not slug:
            continue
        entry = article_entry(article)
        by_slug.setdefault(slug, entry)
        path = keyword_path(entry["keywords"])
        if not path:
            continue
        if path in by_path:
            duplicates.append(entry)
        else:
            by_path[path] = entry
    return by_slug, by_path, duplicates


def resolve_existing(page: dict, by_slug: dict, by_path: dict) -> dict | None:
    """Find the article that already carries this page, by path first."""
    entry = by_path.get(page["path"])
    if entry is not None:
        return entry
    return by_slug.get(page["slug"])


def discover_pages(docs_root: Path) -> list[dict]:
    pages = []
    for path in sorted(docs_root.rglob("*")):
        if not path.is_file() or path.suffix not in {".mdx", ".md"}:
            continue
        if path.name in SKIP_NAMES:
            continue
        rel = path.relative_to(docs_root).as_posix()
        if rel.startswith(".") or "/." in rel:
            continue
        if any(p in rel.split("/") for p in ("scripts", "images", "logo", "node_modules", ".github")):
            continue
        meta, body = strip_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        md = mdx_to_markdown(body)
        raw_title = meta.get("title") or path.stem.replace("-", " ").replace("_", " ").title()
        # FernDesk 400s on bare snake_case problem codes as titles (COR-444).
        if "_" in raw_title and " " not in raw_title:
            desc = (meta.get("description") or "").split(".")[0].strip()
            nice = raw_title.replace("_", " ").title()
            title = f"{desc} ({raw_title})" if desc else nice
        else:
            title = raw_title.replace("_", " ") if "_" in raw_title else raw_title
        slug = rel.rsplit(".", 1)[0]
        if slug.endswith("/index"):
            slug = slug[: -len("/index")] or "index"
        parts = rel.split("/")
        if len(parts) == 1:
            coll = ROOT_FILE_COLLECTION.get(parts[0], "Index")
        else:
            coll = FOLDER_TO_COLLECTION.get(parts[0])
            if not coll:
                continue
        fp = content_fingerprint(md)
        pages.append(
            {
                "path": rel,
                "title": title,
                # FernDesk rejects underscores in slugs (POST 400); normalize.
                "slug": slug.replace("/", "-").replace("_", "-"),
                "collection": coll,
                "markdown": md,
                "fp": fp,
                "keywords": f"source:mintlify;path:{rel};fp:{fp};env:{{ENV}}",
            }
        )
    return pages


def ensure_section(key: str, name: str) -> dict:
    log(f"ensure_section {name!r}")
    for s in list_all(key, "/sections"):
        if s.get("name") == name:
            return s
    return api(key, "/sections", "POST", {"name": name, "slug": name.lower()})


def ensure_collection(key: str, title: str, section_id: str, existing: list) -> dict:
    for c in existing:
        if c.get("sectionId") == section_id and c.get("title") == title and not c.get("parentCollectionId"):
            return c
    c = api(key, "/collections", "POST", {"title": title, "sectionId": section_id})
    existing.append(c)
    time.sleep(0.25)
    return c


def write_cache(cache_path: Path, by_slug: dict, by_path: dict, duplicates: list) -> None:
    cache_path.write_text(
        json.dumps(
            {"by_slug": by_slug, "by_path": by_path, "duplicates": duplicates},
            indent=2,
        )
        + "\n"
    )


def retire_orphaned_articles(
    key: str,
    section: dict,
    by_slug: dict,
    by_path: dict,
    duplicates: list,
    live_paths: set,
    dry: bool = False,
) -> tuple[int, list]:
    """Unpublish Production articles this repository no longer serves.

    The upsert path never deletes, which is what kept FernDesk-only articles
    safe during the migration. That same property let retired pages — the old
    staging mirror, duplicate hub copies, every page renamed since — keep
    serving on the public domain after their MDX was deleted. This is the
    explicit, opt-in way to take them down: it unpublishes, it does not delete.

    Two things are retired:

    1. **Duplicates** — two or more articles carrying the same `path:<rel>`
       marker. FernDesk rewrites a slug it considers taken, so a run that could
       not find its article created a second copy under a fresh hash; the
       canonical entry is kept and the extras are unpublished.
    2. **Orphans** — an article whose `path:<rel>` no longer exists in this
       tree, i.e. the page was deleted or moved.

    Only articles carrying the Mintlify marker are touched. A hand-written
    FernDesk article has no `path:` keyword and is never in scope.
    """
    retired = 0
    failures: list[dict] = []

    def unpublish(entry: dict, why: str) -> bool:
        nonlocal retired
        slug = entry.get("slug") or entry.get("id")
        eid = entry.get("id")
        if not eid:
            return True
        if dry:
            log(f"DRY retire {slug} ({why}) -> {eid}")
            retired += 1
            return True
        try:
            api(key, f"/articles/{eid}/unpublish", "POST", {}, label=str(slug))
        except RuntimeError as e:
            failures.append({"slug": slug, "op": "retire", "error": str(e)})
            log(f"ERROR retire {slug} failed after retries: {e}")
            return False
        retired += 1
        log(f"retired {slug} ({why}) {eid}")
        time.sleep(1.2)
        return True

    for entry in duplicates:
        if "source:mintlify" not in (entry.get("keywords") or ""):
            log(f"retire skip {entry.get('slug')}: not a Mintlify article")
            continue
        unpublish(entry, "duplicate path")

    for slug, entry in sorted(by_slug.items()):
        if not isinstance(entry, dict):
            continue
        keywords = entry.get("keywords") or ""
        if "source:mintlify" not in keywords:
            log(f"retire skip {slug}: not a Mintlify article")
            continue
        path = keyword_path(keywords)
        if path is None:
            # No path marker: nothing in this tree can claim it. Leave it alone
            # rather than unpublishing something a person wrote by hand.
            log(f"retire skip {slug}: no path marker")
            continue
        if path in live_paths:
            continue
        unpublish(entry, f"page gone ({path})")

    if retired or failures:
        log(f"retire: {retired} unpublished, {len(failures)} failed")
    return retired, failures


def main() -> int:
    key = os.environ.get("FERNDESK_API_KEY")
    target = os.environ.get("FERNDESK_TARGET", "production").strip().lower()
    if target != "production":
        log(
            f"ERROR: FERNDESK_TARGET={target!r} is not supported. This repository "
            "publishes to the public FernDesk Production section only; there is no "
            "staging mirror, because staging articles were reachable on "
            "docs.cortex.foundation."
        )
        return 2
    dry = os.environ.get("FERNDESK_DRY_RUN") == "1"
    dry_local = os.environ.get("FERNDESK_DRY_LOCAL") == "1"
    docs_root = Path(os.environ.get("DOCS_ROOT") or Path.cwd()).resolve()
    section_name = SECTION_NAME
    publish = True

    log(f"docs_root={docs_root} target={target} section={section_name} dry={dry} dry_local={dry_local}")
    pages = discover_pages(docs_root)
    log(f"discovered {len(pages)} mintlify pages")

    if dry_local:
        from collections import Counter
        log("by_collection " + json.dumps(Counter(p["collection"] for p in pages)))
        for page in pages[:15]:
            log(f"  {page['collection']}: {page['slug']}")
        if len(pages) > 15:
            log(f"  … +{len(pages)-15} more")
        summary = {"target": target, "pages": len(pages), "mode": "dry-local"}
        log("SUMMARY " + json.dumps(summary))
        return 0

    if not key:
        log("ERROR: FERNDESK_API_KEY missing")
        return 2

    section = ensure_section(key, section_name)
    # Scope to section — unscoped /collections paginated forever in GHA (COR-444).
    colls = list_all(key, f"/collections?sectionId={urllib.parse.quote(str(section['id']))}")
    cache_path = Path(os.environ.get("FERNDESK_SLUG_CACHE", ".ferndesk-slug-cache.json"))
    by_slug: dict = {}
    by_path: dict = {}
    duplicates: list = []
    # A cached slug map cannot resolve identity on its own: FernDesk rewrites a
    # taken slug, so `chat` is stored as `chat-8hul5` and a cache keyed by the
    # requested slug never matches. Scan the section unless the cache carries
    # the path index too (written by this version of the script).
    cache_usable = False
    if cache_path.exists() and os.environ.get("FERNDESK_FULL_SCAN") != "1":
        try:
            cached = json.loads(cache_path.read_text())
            if isinstance(cached, dict) and "by_path" in cached:
                by_slug = cached.get("by_slug") or {}
                by_path = cached.get("by_path") or {}
                duplicates = cached.get("duplicates") or []
                cache_usable = True
                log(f"loaded slug cache {len(by_slug)} / {len(by_path)} paths from {cache_path}")
            else:
                log(f"ignoring legacy slug cache at {cache_path} (no path index)")
        except Exception:
            log(f"slug cache at {cache_path} is unreadable; rescanning")
    if not cache_usable:
        log("scanning articles for section (set FERNDESK_FULL_SCAN=1 to force)…")
        articles = [
            a
            for a in list_all(
                key,
                f"/articles?sectionId={urllib.parse.quote(str(section['id']))}",
                max_pages=200,
            )
            if a.get("sectionId") == section["id"]
        ]
        by_slug, by_path, duplicates = index_articles(articles)
        write_cache(cache_path, by_slug, by_path, duplicates)
        log(
            f"wrote slug cache {len(by_slug)} articles, {len(by_path)} paths, "
            f"{len(duplicates)} duplicates"
        )
        if duplicates:
            log(
                "DUPLICATES "
                + json.dumps([d.get("slug") for d in duplicates])
                + " (rerun with FERNDESK_RETIRE=1 to unpublish them)"
            )

    created = updated = skipped = failed = 0
    retired = 0
    retire_orphans = os.environ.get("FERNDESK_RETIRE") == "1"
    failures: list[dict] = []
    for page in pages:
        page["keywords"] = page["keywords"].replace("{ENV}", target)
        coll = ensure_collection(key, page["collection"], section["id"], colls)
        existing = resolve_existing(page, by_slug, by_path)
        body_common = {
            "title": page["title"],
            "markdown": page["markdown"],
            "collectionId": coll["id"],
            "sectionId": section["id"],
            "slug": page["slug"],
            "keywords": page["keywords"],
            "metaDescription": f"Cortex docs ({target}): {page['title']}",
        }
        if existing:
            eid = existing["id"] if isinstance(existing, dict) else existing
            estatus = existing.get("status") if isinstance(existing, dict) else None
            ekw = (existing.get("keywords") or "") if isinstance(existing, dict) else ""
            if dry:
                log(f"DRY update {page['slug']} -> {eid}")
                skipped += 1
                continue
            # Skip PATCH when Mintlify fingerprint already present (saves write quota).
            if page["fp"] and f"fp:{page['fp']}" in ekw:
                skipped += 1
                log(f"skip unchanged {page['slug']}")
                continue
            try:
                api(key, f"/articles/{eid}", "PATCH", body_common, label=page["slug"])
                if publish and estatus != "published":
                    time.sleep(0.15)
                    api(key, f"/articles/{eid}/publish", "POST", {}, label=page["slug"])
            except RuntimeError as e:
                # One stuck article must not abort the remaining pages; the
                # failure still fails the run and lands in SUMMARY.
                failed += 1
                failures.append({"slug": page["slug"], "op": "update", "error": str(e)})
                log(f"ERROR update {page['slug']} failed after retries: {e}")
                continue
            by_slug[page["slug"]] = {
                "id": eid,
                "status": "published" if publish else (estatus or "draft"),
                "keywords": page["keywords"],
            }
            by_path[page["path"]] = by_slug[page["slug"]]
            write_cache(cache_path, by_slug, by_path, duplicates)
            updated += 1
            log(f"updated {page['slug']}")
            time.sleep(1.2)
            continue

        if dry:
            log(f"DRY create {page['slug']} in {page['collection']}")
            created += 1
            continue
        # Lookup-before-create: avoid POST when slug already exists but missed cache.
        looked = None
        try:
            for a in list_all(
                key,
                f"/articles?sectionId={urllib.parse.quote(str(section['id']))}&slug={urllib.parse.quote(page['slug'])}",
                max_pages=3,
            ):
                if a.get("slug") == page["slug"]:
                    looked = a
                    break
        except RuntimeError as e:
            log(f"slug lookup failed for {page['slug']}: {e}")
        if looked:
            try:
                api(key, f"/articles/{looked['id']}", "PATCH", body_common, label=page["slug"])
                if publish and looked.get("status") != "published":
                    time.sleep(0.3)
                    api(key, f"/articles/{looked['id']}/publish", "POST", {}, label=page["slug"])
            except RuntimeError as e:
                failed += 1
                failures.append({"slug": page["slug"], "op": "lookup-update", "error": str(e)})
                log(f"ERROR lookup-update {page['slug']} failed after retries: {e}")
                continue
            by_slug[page["slug"]] = {
                "id": looked["id"],
                "status": looked.get("status") or "published",
                "keywords": page["keywords"],
            }
            by_path[page["path"]] = by_slug[page["slug"]]
            write_cache(cache_path, by_slug, by_path, duplicates)
            updated += 1
            log(f"lookup-update {page['slug']}")
            time.sleep(1.5)
            continue

        try:
            art = api(
                key,
                "/articles",
                "POST",
                {**body_common, "publish": publish},
                label=page["slug"],
            )
        except RuntimeError as e:
            # Slug may already exist (pagination/cache miss) — recover via lookup + PATCH.
            msg = str(e)
            if "409" in msg or "already" in msg.lower() or "slug" in msg.lower() or "422" in msg:
                log(f"create conflict for {page['slug']}; looking up existing…")
                found = None
                for a in list_all(
                    key,
                    f"/articles?sectionId={urllib.parse.quote(str(section['id']))}&slug={urllib.parse.quote(page['slug'])}",
                    max_pages=5,
                ):
                    if a.get("slug") == page["slug"]:
                        found = a
                        break
                if found:
                    art = found
                    api(key, f"/articles/{art['id']}", "PATCH", body_common, label=page["slug"])
                    if publish and art.get("status") != "published":
                        time.sleep(0.3)
                        api(key, f"/articles/{art['id']}/publish", "POST", {}, label=page["slug"])
                    by_slug[page["slug"]] = {
                        "id": art["id"],
                        "status": art.get("status") or "published",
                        "keywords": page["keywords"],
                    }
                    by_path[page["path"]] = by_slug[page["slug"]]
                    write_cache(cache_path, by_slug, by_path, duplicates)
                    updated += 1
                    log(f"recovered-update {page['slug']}")
                    time.sleep(1.5)
                    continue
            # Still stuck: one page must not abort the remaining pages, but the
            # failure is recorded and fails the run.
            failed += 1
            failures.append({"slug": page["slug"], "op": "create", "error": str(e)})
            log(f"ERROR create {page['slug']} failed after retries: {e}")
            continue
        # FernDesk may rewrite the slug it was given; record what it actually
        # stored so a later run can find this article again.
        stored_slug = art.get("slug") or page["slug"]
        by_slug[stored_slug] = {
            "id": art.get("id"),
            "status": art.get("status") or ("published" if publish else "draft"),
            "keywords": page["keywords"],
            "slug": stored_slug,
        }
        by_path[page["path"]] = by_slug[stored_slug]
        write_cache(cache_path, by_slug, by_path, duplicates)
        created += 1
        log(f"created {stored_slug} {art.get('id')}")
        time.sleep(1.5)

    if retire_orphans:
        retired, retire_failures = retire_orphaned_articles(
            key, section, by_slug, by_path, duplicates, {p["path"] for p in pages}, dry=dry
        )
        failed += len(retire_failures)
        failures.extend(retire_failures)

    summary = {
        "target": target,
        "section_id": section["id"],
        "pages": len(pages),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
        "duplicates": len(duplicates),
    }
    if retire_orphans:
        summary["retired"] = retired
    if failures:
        summary["failed_slugs"] = [f["slug"] for f in failures]
        log("FAILURES " + json.dumps(failures))
    log("SUMMARY " + json.dumps(summary))
    Path(os.environ.get("FERNDESK_SUMMARY_PATH") or "ferndesk-sync-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    if failures:
        log(
            f"ERROR {failed} of {len(pages)} pages failed after retries "
            "(see FAILURES above); rerun the sync once the rate limit clears"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
