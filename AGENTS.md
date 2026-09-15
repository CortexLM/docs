# Cortex public documentation — agent guide

This repository is the source of truth for **`docs.cortex.foundation`**, the
public product documentation site for Cortex. It is an end-user site. Read this
file before editing anything in it.

Edit the site at the repository root. `apps/docs` does not exist here; that path
was the former Mintlify directory in `CortexLM/backend`.

---

## 1. What this site is

`docs.cortex.foundation` is served by the **FernDesk** help center. A GitHub
Action syncs this repository's MDX into the FernDesk **Production** section,
which is what the public domain serves. See [`scripts/FERNDESK.md`](scripts/FERNDESK.md).

Two consequences shape every rule below:

1. **Production only.** There is no staging mirror. Nothing that is not ready
   for a customer to read belongs in this tree. `FERNDESK_TARGET` must be
   `production`; the sync exits `2` for anything else.
2. **Deleting a file does not delete the article.** The sync upserts and never
   deletes, so a page removed here keeps serving until it is retired
   (`FERNDESK_RETIRE=1`, see §7). Renaming a page has the same effect.

## 2. The information architecture

Seven navigation tabs. This list is the contract: keep it this shape.

| Tab | What belongs there |
| --- | --- |
| **Get started** | Quickstart, what Cortex is, accounts, plans, downloads, settings, security, status, troubleshooting |
| **Chat** | The conversation product — projects, Library, canvases, plans, memory, models, tools, research, media |
| **Code** | The coding agent — sessions, Ask / Plan / Agent, GitHub, Cloud runtimes, hosts, review |
| **Bot** | The computer-using agent — computer, tools, approvals, routines, skills, desktop app |
| **CLI** | The terminal client — install, sign in, TUI, slash commands, modes, goals, sessions, headless, configuration, extend |
| **API** | Public API overview, the problem-document format, and the error-code catalog |
| **Changelog** | Dated release notes |

The tree mirrors a platform docs site: **Get started → Build by product →
API reference → Operate**. Home links in that order.

### Products that exist in public navigation

**Chat · Code · Bot · CLI**, plus **API** as reference. That is the whole list.

There is no fourth product app. A product may not be added to `docs.json`, the
navbar, the footer, the home page, or a product switcher without an explicit
request. If a surface is not in the list above, document it as a feature of the
product that owns it — not as a new vertical.

### Where things live

| Page kind | Path |
| --- | --- |
| Product hubs | `chat/index.mdx`, `code/index.mdx`, `bot/index.mdx`, `cli/index.mdx` |
| Product guides | `chat/<topic>.mdx`, `code/<topic>.mdx`, `bot/<topic>.mdx` |
| Error pages | `problems/<snake_case_code>.mdx` — the filename is the wire `code` |
| Cross-product | `getting-started/`, `security/`, `api/`, `status.mdx`, `changelog.mdx` |
| Home | `index.mdx` |

Keep paths short and human. Do not add a page whose only job is to list other
pages that the sidebar already lists — the hub `CardGroup` does that job.

## 3. Never publish

The site is end-user visible. These are hard rules, and CI checks most of them:

- **Staging.** No staging pages, staging nav entries, staging redirects, staging
  hosts, or copy telling a customer to use staging. Staging was publicly
  reachable at `/staging/*` once; it must not happen again.
- **Authentication and session internals.** No `/auth/`, `/oauth/`,
  `refresh_token`, `cortex_rt`, WorkOS, client secrets, device-code internals, or
  identity-provider wire protocol. Users sign in through the product.
- **Private API routes.** Only paths registered in the backend router may be
  documented, and only in inline code or tables (fenced examples are not
  scanned). Do not invent endpoints.
- **Farm, fleet, and operator detail.** No host inventories, node names,
  capacity numbers, backend runbooks, SOC 2 notes, or internal incident tooling.
  Engineering documentation lives in `CortexLM/backend/docs`.
- **Credentials.** No API keys, tokens, cookies, or real customer data — in
  MDX, in examples, or in a commit.
- **Competitors.** No competitor product names in copy, titles, or `docs.json`.
- **Wrong domains.** Only `cortex.foundation`, `api.cortex.foundation`,
  `docs.cortex.foundation`, `status.cortex.foundation`, and
  `software.cortex.foundation` (plus `releases.cortex.foundation` for desktop
  builds). The retired `.sh` and `.dev` hosts, and any `cortex-ide.com` URL, must
  not appear anywhere in this tree.

## 4. Writing rules

- **English product copy.** Product names are never translated: Chat, Code, Bot,
  CLI, and the model names.
- **Tight pages.** Prefer fewer sharp pages over many thin ones. If a section
  would be three sentences and a table, it belongs in the page above it.
- **Lead with the outcome.** First sentence says what the thing does for the
  reader. No "How can we help" preamble, no marketing throat-clearing.
- **Tables for comparisons**, `<Steps>` for procedures, `<Accordion>` for
  questions a reader arrives with, `<Card>` for a hub's navigation.
- **Cortex surface names, never vendors.** User-facing text names a product
  surface. `The coding service is temporarily unavailable`, not a subprocessor.
- **Error copy** links the code page: `[`rate_limited`](/problems/rate_limited)`.
- **One term per concept.** "Session" is a Code session, "chat" is a Chat
  conversation, "plan" is a Chat task list, "routine" is a Bot schedule.
- Do not restate `docs.json` in prose. If the sidebar shows it, the page does not
  need to.

## 5. Visuals

- Heroes that depict the product are **real Cortex screenshots** in
  `images/product/` (web app) and `images/cli/` (terminal, vendored from
  `CortexLM/cli`).
- **Every page shows a distinct capture.** One screenshot is not reused on two
  pages; `images/product/README.md` maps file → page.
- **No fake UI.** `images/frames/*.svg` and `scripts/generate-docs-frames.py`
  are retired and deleted; CI fails any MDX that links a `/images/frames/`
  plate. Never add an abstract product-window SVG, a pixel plate, or a marked
  placeholder. A member-only surface ships without a frame until a real capture
  exists.
- **CTAs are ink on cream** (`.ink-btn`, `.ink-btn-quiet` in `custom.css`).
  Brand green `#1F4945` is for accents, focus rings, and frames — never a filled
  hero CTA, and never a `navbar.primary` button.
- Banner art in `images/banners/` belongs inside `CardGroup` grids on Home and
  the hubs — not as a lone full-width `Card`.
- Navbar stays **Home + Documentation**. Chat | Code | Bot | CLI are
  documentation tabs, not top-nav chrome.

## 6. Editing a page

1. Find the page in the §2 tree; put the change in the page that owns the topic.
2. Keep frontmatter `title` short and the `description` a complete sentence.
3. Link to other pages by path (`/chat/tools`), never by URL.
4. If the page moves, add a `redirects` entry in `docs.json` **and** plan a
   retire pass (§7) — the old FernDesk article is still published.
5. Run the checks in §8 before committing.

Adding a navigation entry means the MDX must exist; CI fails a `docs.json` slug
with no page, and a page that no navigation entry reaches is dead weight.

## 7. FernDesk sync rules

- The workflow runs on push to `main` for docs paths, on `workflow_dispatch`,
  and on `repository_dispatch` type `ferndesk-sync` from a backend prod deploy.
- `FERNDESK_TARGET` is always `production`. A staging target is refused.
- **Article identity is the MDX path, not the slug.** FernDesk rewrites a slug
  it considers taken (`chat` → `chat-8hul5`), so the sync resolves its article
  by the `path:<rel>` marker in `keywords`. Do not add code that matches on slug
  alone: that is what produced the site's duplicate `index-*` and `chat-*`
  articles.
- The sync **upserts and never deletes**. Deleting or renaming a page leaves its
  article published until you retire it:

  ```bash
  FERNDESK_RETIRE=1 python3 scripts/ferndesk_sync.py
  ```

  Retire unpublishes, never deletes, and only touches articles carrying the
  Mintlify fingerprint (`source:mintlify` in `keywords`). It takes down
  duplicate copies of one page and articles whose page no longer exists. A
  hand-written FernDesk article is never in scope.
- The sync prints a `DUPLICATES` line and sets `SUMMARY.duplicates` when one
  page has more than one article. Treat a non-zero count as a cleanup task, not
  a curiosity.
- Slugs are requested as the MDX path with `/` and `_` replaced by `-`, minus
  `.mdx`, with a trailing `/index` dropped. `chat/quickstart.mdx` requests
  `chat-quickstart`, though FernDesk may store a suffixed variant.
- FernDesk-only articles are not this repository's content. Do not delete them
  from the help center UI as part of a docs change.
- Never paste `FERNDESK_API_KEY` into chat, a PR, or a commit. Use the secret
  store.

## 8. Checks

Run all of these before committing. CI runs the same commands.

```bash
node scripts/check-docs-site.mjs
bash scripts/tests/check-docs-site.test.sh
python3 scripts/tests/ferndesk-sync-retry.test.py
npm exec --yes --package=mint@4.2.876 -- mint validate
```

`check-docs-site.mjs` fails on: a problem code without a page or with a wrong
`type` URL; a nav slug or internal href with no MDX; a documented `/v1/…` path
not registered in the backend router; a retired problem-docs host; auth
internals; `/images/frames/` plates; **staging** in navigation, redirects, or
copy; product chrome in the navbar; a brand-green `navbar.primary`; and home
CTAs that are not `.ink-btn`.

Preview locally:

```bash
npx mint dev --no-open
```

### Error-code changes

Problem pages are generated in lockstep with the backend: `PROBLEM_TYPE_BASE` is
`https://docs.cortex.foundation/problems`, and every `ErrorCode` needs a page at
`/problems/{code}` whose filename is the snake_case code. To check the contract
against a backend checkout:

```bash
node scripts/check-docs-site.mjs ../backend
```

The backend owns the API contract and runs this check in its own CI against a
pinned revision of this repository. New codes need both PRs, docs page first.

## 9. Infrastructure

- Custom domains that CNAME to a third party are **Direct CNAME (DNS only)**.
  Never enable orange-cloud Proxied — that causes Cloudflare **Error 1014**
  (Cross-User Banned). This covers `docs.cortex.foundation`,
  `status.cortex.foundation`, the FernDesk Connect domain, and the
  `software.cortex.foundation` / `releases.cortex.foundation` R2 domains.
- Do not change the FernDesk integration, the custom domain, or DNS without an
  explicit request.
- `custom.css` carries the ink CTA and frame styles. Treat it as product chrome:
  change it deliberately, not incidentally.
