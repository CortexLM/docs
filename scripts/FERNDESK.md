# FernDesk sync (this repository → help center)

## One target: Production

`docs.cortex.foundation` serves the FernDesk **Production** section. There is no
staging mirror, and this repository does not create one.

| Section | Status |
|---------|--------|
| **Production** | The only section this repository writes. Served on `docs.cortex.foundation`. |
| ~~Staging~~ | Retired. A staging mirror put pre-prod and draft articles on the public domain. |

`FERNDESK_TARGET` must be `production`. Anything else exits `2` before a single
API call, because a mirror that publishes to the public section is the leak this
repository exists to prevent. Content that is not ready to be public does not
belong in this tree.

Article `keywords` carry `env:production` plus a Mintlify path fingerprint
(`path:<rel>` and `fp:<sha>`), which is what lets a later run skip unchanged
pages and identify articles this repository owns.

## Mechanical sync (durable)

```bash
export FERNDESK_API_KEY=…   # secret only — never paste in chat/PRs
python3 scripts/ferndesk_sync.py
```

GitHub Action: `.github/workflows/ferndesk-sync.yml`

- `push` to `main` (docs paths)
- `workflow_dispatch` (optional `dry_run`, optional `retire`)
- `repository_dispatch` type `ferndesk-sync` (backend prod deploy hook)

Repo secret required: `FERNDESK_API_KEY`.

## Retiring a page

The upsert path never deletes, which is what kept FernDesk-only articles safe
during the migration. The same property means deleting an MDX page does **not**
remove its FernDesk article — it keeps serving on the public domain. That is how
`/staging` and the duplicate hub pages stayed reachable after their MDX was gone.

To take retired pages down, dispatch the workflow with **retire** checked, or:

```bash
FERNDESK_RETIRE=1 python3 scripts/ferndesk_sync.py
```

Retire **unpublishes**; it does not delete. It only touches articles whose
`keywords` carry `source:mintlify`, so a hand-written FernDesk article is never
in scope. Run it after a PR that deletes or renames pages lands on `main`.

## Article identity: the path, not the slug

FernDesk **rewrites a slug it considers taken**: a create for `chat` is stored
as `chat-8hul5`. That broke the obvious identity rule. A run that lost its slug
cache scanned the section, saw `chat-8hul5` but no `chat`, concluded the page
did not exist, and created it again under a fresh hash. Repeated runs produced
the public site's noisy slugs — nine `index-*` articles, a second copy of every
hub, `chat-5ywlo` beside `chat-8hul5`.

Identity now comes from the **`path:<rel>` marker** this script writes into
`keywords` on every create and update. It survives the slug rewrite, so a run
resolves its article by the MDX page it came from and never duplicates it.

Two consequences:

- **The slug cache is a path index.** A cache without `by_path` is ignored and
  the section is rescanned; the file records `by_slug`, `by_path`, and
  `duplicates`.
- **Duplicates are reported, then retired.** The scan groups articles sharing a
  `path:<rel>`; the first is canonical and the rest are listed in a `DUPLICATES`
  line and in `SUMMARY.duplicates`. `FERNDESK_RETIRE=1` unpublishes them, keeping
  the canonical article.

Retire also unpublishes an article whose `path:<rel>` no longer exists in this
tree — a deleted or moved page. An article with no `path:` marker is left alone.

## Slugs

The requested slug is the MDX path with `/` and `_` replaced by `-`, minus the
`.mdx` suffix; `…/index.mdx` drops the trailing `index`. So
`getting-started/quickstart.mdx` is requested as `getting-started-quickstart`,
and `problems/not_found.mdx` as `problems-not-found`.

FernDesk may store something else if the slug is taken — see above. Do not
reason about an article's URL from this function alone; resolve it by path.
Because a move produces a new article and orphans the old one, prefer editing a
page in place, and when you must move it, plan the retire pass in the same PR.

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

## Slugs

The FernDesk slug is the MDX path with `/` replaced by `-` and underscores by
`-`, minus the `.mdx` suffix; `…/index.mdx` drops the trailing `index`. So
`getting-started/quickstart.mdx` syncs as `getting-started-quickstart`, and
`problems/not_found.mdx` as `problems-not-found`.

This is a one-way function. Renaming or moving an MDX page therefore produces a
**new** article and orphans the old one, which then needs a `FERNDESK_RETIRE`
run. Prefer editing a page in place over moving it, and when you must move it,
plan the retire pass in the same PR.

## Factory Droid path (agent)

When Manager Deploy lands **prod** and content needs judgment (rewrites, gap
fill, migration QA), launch Factory Droid only:

- model: `custom:deepseek/deepseek-v4.1-flash`
- effort: **medium**
- **never** Cursor Cloud / CloudAgent, **never** `deepseek-v4-pro`

Prompt the Droid to run `scripts/ferndesk_sync.py` against the tip of
`CortexLM/docs` main, then report the SUMMARY JSON. Do not paste the API key
into the prompt — use the Droid/host secret store.

## Safety

- Sync **upserts** by Mintlify path. It does not delete.
- `FERNDESK_RETIRE=1` is the only path that unpublishes, it is opt-in, and it is
  limited to articles carrying the Mintlify fingerprint.
- Staging is refused. There is no code path that creates or writes a Staging
  section.
- `python3 scripts/tests/ferndesk-sync-retry.test.py` covers the write-path
  retry policy, the production-only guard, path-based identity against rewritten
  slugs, and the retire path offline (faked transport, virtual clock).

## Cloudflare / GitHub Actions

FernDesk sits behind Cloudflare. GHA's stock Python `urllib` TLS fingerprint triggers
**Error 1010** (`browser_signature_banned`). The sync script uses `curl_cffi` with
`impersonate="chrome"` in CI (Chrome-like User-Agent + Accept; retries 403/1010 with
backoff). Local runs fall back to urllib only if `curl_cffi` is not installed.

Separately: the FernDesk UI needs a **Connect domain** for `docs.cortex.foundation`
HTTPS. That custom-domain 403 is unrelated to CF 1010 on `api.ferndesk.com`.

When that record goes in, use a **Direct CNAME (DNS only)** — **do not enable
orange-cloud Proxied**; that causes Cloudflare **Cross-User Banned** (Error 1014).
The same rule holds for every other Cortex custom domain that CNAMEs to a
third-party host: [`README.md`](../README.md#custom-domain-dns).
