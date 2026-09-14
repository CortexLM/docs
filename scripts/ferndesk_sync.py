#!/usr/bin/env python3
"""Sync CortexLM/docs (Mintlify MDX) → FernDesk help center.

Env:
  FERNDESK_API_KEY   required (Bearer). Never print/log the value.
  FERNDESK_TARGET    production|staging (default: production)
  FERNDESK_DRY_RUN   1 = plan only (still needs API unless FERNDESK_DRY_LOCAL=1)
  FERNDESK_DRY_LOCAL 1 = discover pages only, no API
  FERNDESK_FULL_SCAN 1 = rebuild slug cache by listing all articles
  FERNDESK_SLUG_CACHE path to slug→id cache (default .ferndesk-slug-cache.json)
  DOCS_ROOT          docs repo root (default: cwd)

Idempotent upsert by slug. Never deletes FernDesk-only articles (safe migration).
"""
from __future__ import annotations

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

FOLDER_TO_COLLECTION = {
    "getting-started": "Getting Started",
    "chat": "Chat",
    "code": "Code",
    "bot": "Bot",
    "cli": "Cli",
    "design": "Design",
    "api": "Api",
    "security": "Security",
    "problems": "Problems",
    "changelog": "Changelog",
}

ROOT_FILE_COLLECTION = {
    "index.mdx": "Index",
    "platform.mdx": "Platform",
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


def api(key: str, path: str, method: str = "GET", body: dict | None = None, retries: int = 6):
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

    for i in range(retries):
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
                    if resp.status_code in (429, 502, 503, 504) or _is_cf_1010(
                        resp.status_code, txt
                    ):
                        wait = min(90, 3 * (2**i))
                        kind = (
                            "cf1010/403"
                            if _is_cf_1010(resp.status_code, txt)
                            else f"rate/limit {resp.status_code}"
                        )
                        log(f"{kind}; sleep {wait}s")
                        time.sleep(wait)
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
            if e.code in (429, 502, 503, 504) or _is_cf_1010(e.code, txt):
                wait = min(90, 3 * (2**i))
                kind = "cf1010/403" if _is_cf_1010(e.code, txt) else f"rate/limit {e.code}"
                log(f"{kind}; sleep {wait}s")
                time.sleep(wait)
                continue
            raise RuntimeError(last) from e
        except urllib.error.URLError as e:
            last = f"{method} {path} -> URLError {e}"
            wait = min(90, 3 * (2**i))
            log(f"transport error; sleep {wait}s ({e})")
            time.sleep(wait)
            continue
        except RuntimeError:
            raise
        except Exception as e:
            last = f"{method} {path} -> {type(e).__name__} {e}"
            wait = min(90, 3 * (2**i))
            log(f"transport error; sleep {wait}s ({e})")
            time.sleep(wait)
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
        if cursor:
            sep = "&" if "?" in path else "?"
            p = f"{path}{sep}cursor={urllib.parse.quote(cursor)}"
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
        title = meta.get("title") or path.stem.replace("-", " ").title()
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
                "slug": slug.replace("/", "-"),
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


def main() -> int:
    key = os.environ.get("FERNDESK_API_KEY")
    target = os.environ.get("FERNDESK_TARGET", "production").strip().lower()
    if target not in ("production", "staging"):
        log("ERROR: FERNDESK_TARGET must be production|staging")
        return 2
    dry = os.environ.get("FERNDESK_DRY_RUN") == "1"
    dry_local = os.environ.get("FERNDESK_DRY_LOCAL") == "1"
    docs_root = Path(os.environ.get("DOCS_ROOT") or Path.cwd()).resolve()
    section_name = "Production" if target == "production" else "Staging"
    publish = target == "production"

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
    cache_path = Path(os.environ.get("FERNDESK_SLUG_CACHE", f".ferndesk-slug-cache-{target}.json"))
    by_slug: dict = {}
    cache_loaded = False
    if cache_path.exists() and os.environ.get("FERNDESK_FULL_SCAN") != "1":
        try:
            by_slug = json.loads(cache_path.read_text())
            cache_loaded = True
            log(f"loaded slug cache {len(by_slug)} from {cache_path}")
        except Exception:
            by_slug = {}
    if (not cache_loaded) or os.environ.get("FERNDESK_FULL_SCAN") == "1":
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
        by_slug = {
            a.get("slug"): {"id": a["id"], "status": a.get("status")}
            for a in articles
            if a.get("slug")
        }
        cache_path.write_text(json.dumps(by_slug, indent=2) + "\n")
        log(f"wrote slug cache {len(by_slug)}")

    created = updated = skipped = 0
    for page in pages:
        page["keywords"] = page["keywords"].replace("{ENV}", target)
        coll = ensure_collection(key, page["collection"], section["id"], colls)
        existing = by_slug.get(page["slug"])
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
            if dry:
                log(f"DRY update {page['slug']} -> {eid}")
                skipped += 1
                continue
            api(key, f"/articles/{eid}", "PATCH", body_common)
            if publish and estatus != "published":
                time.sleep(0.15)
                api(key, f"/articles/{eid}/publish", "POST", {})
            updated += 1
            log(f"updated {page['slug']}")
            time.sleep(0.3)
            continue

        if dry:
            log(f"DRY create {page['slug']} in {page['collection']}")
            created += 1
            continue
        art = api(key, "/articles", "POST", {**body_common, "publish": publish})
        by_slug[page["slug"]] = {
            "id": art.get("id"),
            "status": art.get("status") or ("published" if publish else "draft"),
        }
        cache_path.write_text(json.dumps(by_slug, indent=2) + "\n")
        created += 1
        log(f"created {page['slug']} {art.get('id')}")
        time.sleep(0.4)

    summary = {
        "target": target,
        "section_id": section["id"],
        "pages": len(pages),
        "created": created,
        "updated": updated,
        "skipped": skipped,
    }
    log("SUMMARY " + json.dumps(summary))
    Path(os.environ.get("FERNDESK_SUMMARY_PATH") or "ferndesk-sync-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
