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

The site has **no images**. Every visual is an icon (Font Awesome, the Mintlify
starter default).

## Checks

```bash
node scripts/check-docs-site.mjs
bash scripts/tests/check-docs-site.test.sh
node scripts/tests/docs-ui.test.mjs
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
- a page carries an image, lacks a title, description, or icon, repeats another page's title, or has a description over 160 characters
- navigation is not `navigation.tabs` with a tab for each of Chat, Code, Bot, CLI, Design, and Security, each tab and group carrying an icon
- public MDX documents `/auth/`, `/oauth/`, `refresh_token`, the identity vendor, or the session cookie
- `api/authentication.mdx` or `api/oauth.mdx` exist, or the navigation lists them

Do not invent endpoints. There is no inference Platform API section here; see
`reference/platform-api.mdx`. Sign in via the app; this tree has no auth stack.
