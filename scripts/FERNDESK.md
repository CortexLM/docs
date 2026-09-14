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

## Factory Droid path (agent)

When Manager Deploy lands **prod** and content needs judgment (rewrites, gap fill, migration QA), launch Factory Droid only:

- model: `custom:deepseek/deepseek-v4.1-flash`
- effort: **medium**
- **never** Cursor Cloud / CloudAgent, **never** `deepseek-v4-pro`

Prompt the Droid to run `scripts/ferndesk_sync.py` against the tip of `CortexLM/docs` main with `FERNDESK_TARGET=production`, then report the SUMMARY JSON. Do not paste the API key into the prompt — use the Droid/host secret store.

## Safety

- Sync **upserts** by slug; it does **not** delete FernDesk-only articles.
- Mintlify remains the source of truth in git until cutover is complete.

## Cloudflare / GitHub Actions

FernDesk sits behind Cloudflare. GHA's stock Python `urllib` TLS fingerprint triggers
**Error 1010** (`browser_signature_banned`). The sync script uses `curl_cffi` with
`impersonate="chrome"` in CI (Chrome-like User-Agent + Accept; retries 403/1010 with
backoff). Local runs fall back to urllib only if `curl_cffi` is not installed.

Separately: the FernDesk UI still needs **Connect domain** for `docs.cortex.foundation`
HTTPS. That custom-domain 403 is unrelated to CF 1010 on `api.ferndesk.com`.
