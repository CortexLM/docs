# Cortex docs (`docs.cortex.foundation`)

Public product documentation for **Cortex Chat**, **Cortex Code**, **Cortex Bot**, the **Cortex CLI**,
and **Cortex Design**. This site is **end-user visible**. It does **not** document
login, sessions, refresh tokens, OAuth wire protocol, or other non-public APIs.

This repository is a [Mintlify](https://mintlify.com) site, migrated from
`CortexLM/backend` at `782b054` (the former `apps/docs` directory).
Engineering / operator documentation stays in
[`CortexLM/backend/docs`](https://github.com/CortexLM/backend/tree/main/docs)
(runbooks, SOC 2 notes, farm internals). Do not merge the two trees.

## Preview

```bash
git clone https://github.com/CortexLM/docs.git
cd docs
npx mint dev --no-open
```

Requires Node 20.17+. The site is intended to publish at
`https://docs.cortex.foundation`. Connecting the custom domain is an operator
step in the Mintlify dashboard. Connect `CortexLM/docs`, branch `main`, with
the content directory set to the repository root (not `apps/docs`).

### Custom-domain DNS

Every Cortex custom domain that CNAMEs to a third-party hostname is a
**Direct CNAME (DNS only)** — `docs.cortex.foundation` (Mintlify),
`status.cortex.foundation` (status page), and the
`software.cortex.foundation` / `releases.cortex.foundation` R2 custom
domains owned by
[`CortexLM/backend`](https://github.com/CortexLM/backend)
(`docs/software-cdn.md`).

> **Use a Direct CNAME (DNS only). Do not enable orange-cloud Proxied** — that
> causes Cloudflare **Cross-User Banned** (Error 1014).

## Structure

Mintlify is the single source of truth for the public docs. There is no
downstream mirror to sync: the site publishes from this repository, branch
`main`, and `docs.json` is the whole navigation.

| Tab | Holds | Entry point |
| --- | --- | --- |
| Get started | Quickstart, what Cortex is, accounts, plans, settings, downloads, help | `getting-started/quickstart` |
| Chat | The conversation product — projects, Library, plans, models, tools, research, media | `chat/index` |
| Code | The coding agent — sessions, modes, GitHub, runtimes, review | `code/index` |
| Bot | The computer-using agent — computer, tools, approvals, routines, skills | `bot/index` |
| CLI | The terminal front-end to Code — install, TUI, slash commands, sessions, headless, extend | `cli/index` |
| Design | Canvases and the Design library | `design/index` |
| API | The RFC 9457 problem format and the catalog of error codes | `api/overview` |
| Changelog | Dated release notes, and the deferred Platform API | `changelog` |

Each product tab opens on a single hub page (`<product>/index.mdx`). Do not
re-introduce a second overview page beside it — one entry point per product,
with the task guides beneath it in the sidebar.

Every page ends with a **Related** or **Next** section so a reader is never at
a dead end, and every page carries a `title` and a `description` in its
frontmatter. Product pages also carry an `image` for link previews.

## Checks

```bash
node scripts/check-docs-site.mjs
bash scripts/tests/check-docs-site.test.sh
node scripts/tests/docs-ui.test.mjs
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

Do not invent endpoints. There is no inference Platform API section here — see
`platform.mdx`. Sign in via the app; this tree has no auth stack.

`scripts/check-docs-site.mjs` enforces all of the above, including that every
`docs.json` navigation slug resolves to a page. Run it before pushing; a
sidebar link with no MDX behind it would otherwise publish as a 404.

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
captured. Do not add abstract product-window SVGs. `images/frames/` is
retired. Banner card art (`images/banners/`) belongs inside `CardGroup`
grids on Home and the hubs — never as a lone full-width `Card`. Cream, ink,
`#1F4945` focus — no violet.

Top navbar is Mintlify **Home + Documentation**, not the Chat | Code | Bot
product switcher. Get started / Chat / Code / Bot / CLI / Design stay as
documentation tabs. Competitor product names never appear in copy,
titles, or `docs.json`.
