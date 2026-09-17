# Cortex docs (`docs.cortex.foundation`)

Public documentation for the Cortex applications: **Cortex Chat**, **Cortex
Code**, **Cortex Bot**, the **Cortex CLI**, **Cortex Design**, and **Cortex
Security**, plus a Reference tab (errors, models, limits, privacy, status,
the Bounty program, and the changelog). The site is **end-user visible**. It
does not document sign-in internals, private API routes, or infrastructure.

This repository is a [Mintlify](https://mintlify.com) site built from the
Mintlify starter kit (`mint` theme, Font Awesome icons, tabs in the navbar).
Engineering and operator documentation stays in
[`CortexLM/backend/docs`](https://github.com/CortexLM/backend/tree/main/docs).
Do not merge the two trees.

## Preview

```bash
git clone https://github.com/CortexLM/docs.git
cd docs
npx mint dev --no-open
```

Requires Node 20.17+. The site publishes at `https://docs.cortex.foundation`
from branch `main`, with the content directory set to the repository root.

### Custom-domain DNS

Every Cortex custom domain that CNAMEs to a third-party hostname is a
**Direct CNAME (DNS only)**: `docs.cortex.foundation` (Mintlify),
`status.cortex.foundation` (status page), and the
`software.cortex.foundation` / `releases.cortex.foundation` download hosts
owned by [`CortexLM/backend`](https://github.com/CortexLM/backend).

> **Use a Direct CNAME (DNS only). Do not enable proxying** on these records.

## Structure

`docs.json` is the whole navigation. It uses `navigation.tabs`, one tab per
application, so a reader picks the product from the navbar:

| Tab | Holds | Opens on |
| --- | --- | --- |
| Get started | Home, quickstart, what Cortex is, choosing a product, accounts and sign-in, two-factor, plans and quotas, settings, data and privacy, notifications, interface language, ways to run Cortex, the desktop app, troubleshooting, shortcuts, bug reports, FAQ, glossary | `index` |
| Chat | Conversations, models and thinking, attachments, streaming and reconnects, voice, canvases, document export, projects, Library, file sharing, memory, Planning, scheduled tasks, built-in tools, Deep Research, image generation, origin check, Cortex Data, skills, Connectors, MCP servers, page tools, sharing and teams, troubleshooting | `chat/index` |
| Code | Sessions, Ask / Plan / Agent, approvals, changes and diffs, tickets, cloud runtimes, environments and images, machines, SSH hosts, desktop, GitHub, repositories and branches, automations, notifications, usage, settings, integrations, CLI pointer, review pointer, troubleshooting | `code/index` |
| Bot | Create a bot, talking to a bot, computer, tools, approvals and tool policy, memory, skills, routines, tasks and subagents, connected apps and secrets, inbox, channels, sharing, teach from a demonstration, Bot desktop app, troubleshooting | `bot/index` |
| CLI | Install, sign in, quickstart, the TUI, modes and permissions, Plan and Spec modes, sessions, goals, slash commands, shortcuts, tools, cloud / this PC / SSH, editor integration, headless runs, CI cookbook, configuration, environment variables, data locations, permission policy, MCP, skills, agents and subagents, hooks, plugins, themes, command reference, troubleshooting | `cli/index` |
| Design | Quickstart, canvases, generate and edit, versions, library, export, Bot jobs, Connectors, Design desktop app, settings, troubleshooting | `design/index` |
| Security | Quickstart, how a review works, checks and comments, review policy, repository scans, Cortex Agent runs, installation and repositories, troubleshooting | `security/index` |
| Reference | Errors and the problem catalog, models, limits and quotas, security and privacy, system status, Platform API, the Bounty program (pair a hotkey, file a report, verdicts and scoring, Transparency API), changelog | `reference/errors` |

Each product tab opens on a single hub page (`<product>/index.mdx`) with a card
per page of the tab. Every page carries a `title`, a `description` under 160
characters, an `icon`, and ends with a **Related** section so a reader is
never at a dead end. Titles are unique across the site; where two pages would
otherwise collide (`Sessions` in Code and in the CLI, `Skills` in Chat, Bot,
and the CLI) the title carries the product and `sidebarTitle` keeps the
sidebar short.

Navigation cards and page frontmatter keep their Font Awesome icons (the
Mintlify starter default). Article bodies may also carry product screenshots.

## Product screenshots

Use actual Cortex interfaces captured from Paper and composed with Higgsfield
wallpaper. Do not generate or invent interface controls, imply an unavailable
feature is working, or expose personal data or credentials. Keep the interface
readable and place each screenshot beside the section it explains; reuse a
canonical view instead of repeating near-identical visuals across guides.

Commit exports under `images/product/` as WebP, PNG or JPG (`.jpeg` also works).
Use root-relative URLs and literal, quoted attributes on self-closing `<img />`
tags. Every image needs descriptive, nonempty English alt text. Include its
intrinsic width and height to reserve space while it loads. `<Frame>` may wrap
an image and provide a caption:

```mdx
<Frame caption="Interface preview">
  <img src="/images/product/chat-home-light.webp" alt="Cortex Chat home with its composer and workspace navigation." width="3360" height="2240" loading="lazy" />
</Frame>
```

Only use theme switching when both files are actual matching captures:

```mdx
<Frame caption="Interface preview">
  <div className="block dark:hidden">
    <img src="/images/product/chat-home-light.webp" alt="Cortex Chat home with its composer and workspace navigation." width="3360" height="2240" loading="lazy" />
  </div>
  <div className="hidden dark:block">
    <img src="/images/product/chat-home-dark.webp" alt="Cortex Chat home with its composer and workspace navigation." width="3360" height="2240" loading="lazy" />
  </div>
</Frame>
```

The checkers require existing, nonempty local files and reject path traversal,
symlink escapes, URL encoding, queries, fragments, remote URLs and data URLs.
Image attributes are limited to `src`, `alt`, `width`, `height`, `className`,
`loading`, `decoding` and `title`; expressions, spreads, event handlers and
`srcSet` are not supported. Markdown images, `image:` frontmatter and other
media embeds are not supported; use the checked `<img />` form instead.
Examples inside code spans, fenced blocks and comments are not rendered images.
The shared syntax checks do not require a manifest. The provenance regression
test additionally checks this gallery against `design/docs-images.json`, rejects
`galleryOnly` assets, and catches unused public exports. See
[`design/docs-images.md`](design/docs-images.md) for the composition and
publication policy.

## Checks

```bash
node scripts/check-docs-site.mjs
node scripts/check-docs-content.mjs
bash scripts/tests/check-docs-site.test.sh
bash scripts/tests/check-docs-content.test.sh
node scripts/tests/docs-ui.test.mjs
node scripts/tests/docs-images.test.mjs
npm exec --yes --package=mint@4.2.876 -- mint validate
```

The **Docs site** CI job checks navigation, problem-page URLs, frontmatter,
internal links, and the public content rules without needing access to the
backend.

To also validate against the real API, pass a backend checkout:

```bash
node scripts/check-docs-site.mjs ../backend
```

The backend's **Docs site** job runs this additional check against a pinned
revision of this repository. New error codes need a coordinated docs change:
merge the docs page first, then update the backend's checkout pin in the PR
that adds the code. The full check fails when:

- `PROBLEM_TYPE_BASE` is not `https://docs.cortex.foundation/problems`
- an `ErrorCode` is missing its `/problems/{code}` page, or a page documents a code the API does not emit
- a `docs.json` navigation slug, group root, navbar or footer href, redirect destination, or internal link has no matching MDX page
- a documented `/v1/…` path is not registered in `crates/cortex-api/src/router.rs`
- a screenshot lacks alt text, references a missing or unsafe local file, uses an unsupported format or embeds remote media
- a page lacks a title, description, or icon, repeats another page's title, or has a description over 160 characters
- navigation is not `navigation.tabs` with a tab for each of Chat, Code, Bot, CLI, Design, and Security, each tab and group carrying an icon
- public MDX documents `/auth/`, `/oauth/`, `refresh_token`, the identity vendor, or the session cookie
- `api/authentication.mdx` or `api/oauth.mdx` exist, or the navigation lists them

Do not invent endpoints. There is no inference Platform API section here; see
`reference/platform-api.mdx`. Sign in via the app; this tree has no auth stack.
