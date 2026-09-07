# Cortex docs (`docs.cortex.foundation`)

Public product documentation for **Cortex Chat**, **Cortex Code**, **Cortex Bot**,
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

## Checks

```bash
node scripts/check-docs-site.mjs
bash scripts/tests/check-docs-site.test.sh
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

## Visuals

Brand green `#1F4945` is for doodle accents, not hero CTAs. Home and card
actions use **ink on cream** (`.ink-btn` in `custom.css`) — filled ink, quiet
outline; dark mode inverts to cream ink. Do not add a brand-green Install /
`navbar.primary` button.

Top navbar is Mintlify **Home + Documentation**, not the Chat | Code | Bot
product switcher. Chat / Code / Bot / Design stay as documentation tabs.
