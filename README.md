# Cortex docs (`docs.cortex.foundation`)

Public product documentation for **Cortex Chat**, **Cortex Code**, **Cortex
Bot**, and the **Cortex CLI**, plus the public API error reference. This site is
**end-user visible**. It does **not** document login, sessions, refresh tokens,
OAuth wire protocol, private API routes, or operator runbooks.

This repository is the source of truth. **FernDesk** serves the site: a GitHub
Action syncs the MDX here into the FernDesk **Production** section, which is what
`docs.cortex.foundation` publishes. There is **no staging mirror** — a staging
section was reachable on the public domain once, and the sync now refuses any
target other than `production`.

Editing rules for agents and humans live in [`AGENTS.md`](AGENTS.md). FernDesk
sync mechanics, rate limits, and the retire path live in
[`scripts/FERNDESK.md`](scripts/FERNDESK.md).

Engineering / operator documentation stays in
[`CortexLM/backend/docs`](https://github.com/CortexLM/backend/tree/main/docs)
(runbooks, SOC 2 notes, farm internals). Do not merge the two trees.

## Structure

Seven navigation tabs, mirroring a platform docs site — get started, build by
product, API reference, operate:

| Tab | Contents |
| --- | --- |
| **Get started** | Quickstart, what Cortex is, accounts, plans, downloads, settings, security, status, troubleshooting |
| **Chat** | Projects, Library, canvases, plans, memory, models, tools, Deep Research, images, voice |
| **Code** | Sessions, Ask / Plan / Agent, GitHub, Cloud runtimes, hosts, pull-request review |
| **Bot** | Computer, tools, approvals, routines, skills, desktop app |
| **CLI** | Install, sign in, TUI, slash commands, modes, goals, sessions, headless, configuration, extend |
| **API** | Public API overview, problem-document format, error-code catalog |
| **Changelog** | Dated release notes |

The public products are **Chat · Code · Bot · CLI**. There is no fourth product
app, and no product is added to `docs.json` or the navbar without an explicit
request.

## Preview

```bash
git clone https://github.com/CortexLM/docs.git
cd docs
npx mint dev --no-open
```

Requires Node 20.17+. The site publishes at `https://docs.cortex.foundation`.
Connecting the custom domain is an operator step in the FernDesk UI; the
repository holds the content and the sync, not the DNS.

### Custom-domain DNS

Every Cortex custom domain that CNAMEs to a third-party hostname is a
**Direct CNAME (DNS only)** — `docs.cortex.foundation` (FernDesk Connect
domain), `status.cortex.foundation` (status page), and the
`software.cortex.foundation` / `releases.cortex.foundation` R2 custom domains
owned by
[`CortexLM/backend`](https://github.com/CortexLM/backend)
(`docs/software-cdn.md`).

> **Use a Direct CNAME (DNS only). Do not enable orange-cloud Proxied** — that
> causes Cloudflare **Cross-User Banned** (Error 1014).

## Checks

```bash
node scripts/check-docs-site.mjs
bash scripts/tests/check-docs-site.test.sh
python3 scripts/tests/ferndesk-sync-retry.test.py
npm exec --yes --package=mint@4.2.876 -- mint validate
```

The **Docs site** CI job checks navigation, problem-page URLs and the public
content rules without needing access to the backend.

To also validate against the real API, pass a backend checkout:

```bash
node scripts/check-docs-site.mjs ../backend
```

The backend's **Docs site** job runs this additional check against a pinned
revision of this repository. New error codes need a coordinated docs change:
merge the docs page first, then update the backend's checkout pin in the PR
that adds the code. The full check fails when:

- `PROBLEM_TYPE_BASE` is not `https://docs.cortex.foundation/problems`
- an `ErrorCode` is missing its `/problems/{code}` page
- a `docs.json` navigation slug or internal href has no matching MDX page
- a documented `/v1/…` path is not registered in `crates/cortex-api/src/router.rs`
- this tree names a problem-docs host other than `docs.cortex.foundation`
- the top navbar is not Home + Documentation, or it carries Chat | Code | Bot chrome / `navbar.primary`
- the home page uses Mintlify Cards as brand-green Install CTAs instead of `.ink-btn`
- public MDX documents `/auth/`, `/oauth/`, `refresh_token`, WorkOS, or `cortex_rt`
- `api/authentication.mdx` or `api/oauth.mdx` exist, or the API tab lists them
- navigation, a redirect, or page copy points at a **staging** page or host

Do not invent endpoints. There is no inference Platform API section here — see
[`api/overview.mdx`](api/overview.mdx). Sign in via the app; this tree has no
auth stack.

## FernDesk sync

```bash
export FERNDESK_API_KEY=…   # secret only — never paste in chat/PRs
python3 scripts/ferndesk_sync.py
```

GitHub Action: [`.github/workflows/ferndesk-sync.yml`](.github/workflows/ferndesk-sync.yml),
on push to `main` (docs paths), on manual dispatch, and on the backend's prod
deploy hook. `FERNDESK_TARGET` is always `production`; any other value exits `2`.

The sync upserts by slug and **never deletes**, so deleting or renaming a page
leaves its article published. Take retired pages down explicitly:

```bash
FERNDESK_RETIRE=1 python3 scripts/ferndesk_sync.py
```

Retire unpublishes rather than deletes, and only touches articles carrying the
Mintlify fingerprint. Details and the 429 retry policy: [`scripts/FERNDESK.md`](scripts/FERNDESK.md).

## Visuals

Brand green `#1F4945` is for doodle accents, illustration focus rings, and
window frames — not hero CTAs. Home and card actions use **ink on cream**
(`.ink-btn` in `custom.css`) — filled ink, quiet outline; dark mode inverts
to cream ink. Do not add a brand-green Install / `navbar.primary` button.

Guide heroes that depict the product are **live Cortex screenshots** in
`images/product/` plus CLI canon in `images/cli/` (vendored from
CortexLM/cli `docs/media/`). **Every page shows a distinct capture** — no
product frame is reused on two pages; `images/product/README.md` maps each
file to the page that uses it, and lists member-only surfaces still to be
captured. Do not add abstract product-window SVGs: `images/frames/` and
`scripts/generate-docs-frames.py` are retired and deleted. Banner card art
(`images/banners/`) belongs inside `CardGroup` grids on Home and the hubs —
never as a lone full-width `Card`. Cream, ink, `#1F4945` focus — no violet.

Top navbar is **Home + Documentation**, not a product switcher. Get started /
Chat / Code / Bot / CLI / API / Changelog stay as documentation tabs. Competitor
product names never appear in copy, titles, or `docs.json`.
