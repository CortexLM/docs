# FernDesk sync (Mintlify → help center)

## Staging vs Production

FernDesk sections (not tags) are the env boundary:

| Section | Use |
|---------|-----|
| **Production** | Public docs.cortex.foundation content (after custom domain connect) |
| **Staging** | Pre-prod / draft mirrors; unpublished or staging-only articles |

Collections are mirrored under both sections (`Getting Started`, `Chat`, `Code`, `Bot`, …).
Article `keywords` carry `env:production|staging` plus a Mintlify path fingerprint.

## Mechanical sync (durable)

```bash
export FERNDESK_API_KEY=…   # secret only — never paste in chat/PRs
FERNDESK_TARGET=production python3 scripts/ferndesk_sync.py
```

GitHub Action: `.github/workflows/ferndesk-sync.yml`

- `push` to `main` (docs paths)
- `workflow_dispatch` (choose production|staging)
- `repository_dispatch` type `ferndesk-sync` (backend prod deploy hook)

Repo secret required: `FERNDESK_API_KEY`.

## Write-path rate limits (429)

`POST /articles` answers `429` / `{"code":"rate_limited"}` under load. The write
path (article create, update, publish, and collection create) backs off
exponentially — 5s doubling to a 180s cap, the slower ladder 429 needs; 5xx and
CF 1010 keep 3s doubling to 90s — and waits for `Retry-After` (delta-seconds or
HTTP-date) whenever the server sends it and it is larger.

Retries stay bounded on three axes, so a rate-limited run finishes and reports
instead of hanging:

| Env | Default | Meaning |
|-----|---------|---------|
| `FERNDESK_WRITE_RETRIES` | `12` | attempts per write |
| `FERNDESK_WRITE_DEADLINE` | `1800` | seconds of retrying for one write |
| `FERNDESK_WRITE_BUDGET` | `5400` | seconds of retry time for the whole run (`0` disables) |

Reads share the 12-attempt default. A `Retry-After` above 300s is treated as
unusable and the exponential ladder is used instead. Hard 4xx (400/401/404)
fail immediately without retrying.

One page that exhausts its retries does not abort the rest of the run: the sync
continues, then logs a `FAILURES` line, records `failed` / `failed_slugs` in the
SUMMARY, and exits `1`. Nothing is cached for a failed write, so the next run
retries that page cleanly. Re-run the sync (or the workflow) once the limit
clears.

A create that trips a slug conflict (409/422, or a message naming the slug) is
recovered by looking the article up and PATCHing it, so a stale cache or a
pagination miss does not surface as a failure.

## Slugs and titles (FernDesk POST 400)

FernDesk accepts a slug only in `[a-z0-9]+(-[a-z0-9]+)*`. It answers `POST
/articles` with **400** for anything else, so `problems/bad_request` used to be
sent verbatim as `problems-bad_request` and rejected: 19 `problems-*` pages
failed while `problems-conflict`, `problems-forbidden`, and `problems-gone`
created fine.

The MDX file name cannot change — it matches `ErrorCode::as_str` and the page's
`/problems/{code}` type URI — so the slug is sanitized at the sync boundary by
`sanitize_slug()`: lowercased, every run of other characters (`_`, `/`, spaces,
`--`) collapsed to one hyphen, ends trimmed. `problems/bad_request` →
`problems-bad-request`, `api/errors` → `api-errors`.

Two source paths that sanitize to one slug (`a_b.mdx` and `a-b.mdx`) would
silently overwrite one article, so `discover_pages` raises instead of syncing.

Titles are separate: a bare snake_case code is not a usable article title, so a
page whose title is `bad_request` is published as `Bad request (bad_request)`
using its `description`. The title keeps the snake_case code, since that is the
wire contract readers search for.

`scripts/tests/ferndesk-sync-retry.test.py` holds both rules: it runs
`discover_pages` over this repository and fails if any problem page produces an
illegal slug, keeps an underscore, collides with another page, or keeps a bare
snake_case title.

## Factory Droid path (agent)

When Manager Deploy lands **prod** and content needs judgment (rewrites, gap fill, migration QA), launch Factory Droid only:

- model: `custom:deepseek/deepseek-v4.1-flash`
- effort: **medium**
- **never** Cursor Cloud / CloudAgent, **never** `deepseek-v4-pro`

Prompt the Droid to run `scripts/ferndesk_sync.py` against the tip of `CortexLM/docs` main with `FERNDESK_TARGET=production`, then report the SUMMARY JSON. Do not paste the API key into the prompt — use the Droid/host secret store.

## Safety

- Sync **upserts** by slug; it does **not** delete FernDesk-only articles.
- Mintlify remains the source of truth in git until cutover is complete.
- `python3 scripts/tests/ferndesk-sync-retry.test.py` covers the write-path
  retry policy offline (faked transport, virtual clock).

## Cloudflare / GitHub Actions

FernDesk sits behind Cloudflare. GHA's stock Python `urllib` TLS fingerprint triggers
**Error 1010** (`browser_signature_banned`). The sync script uses `curl_cffi` with
`impersonate="chrome"` in CI (Chrome-like User-Agent + Accept; retries 403/1010 with
backoff). Local runs fall back to urllib only if `curl_cffi` is not installed.

Separately: the FernDesk UI still needs **Connect domain** for `docs.cortex.foundation`
HTTPS. That custom-domain 403 is unrelated to CF 1010 on `api.ferndesk.com`.
