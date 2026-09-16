# Cortex public documentation

This is the Mintlify site for `docs.cortex.foundation`. Edit the site at the
repository root. Preview and validation commands are in `README.md`.

- Keep product copy in English and use the Cortex product names and domains:
  Cortex Chat, Cortex Code, Cortex Bot, Cortex Design, Cortex Security, the
  Cortex CLI, Cortex Bounty; `cortex.foundation`, `docs.cortex.foundation`,
  `status.cortex.foundation`, `software.cortex.foundation`.
- The site is end-user documentation. Do not publish sign-in wire protocols,
  session or token internals, credentials, private API routes, infrastructure
  details, vendor names, or backend operator runbooks. Competitor product
  names never appear in copy, titles, or `docs.json`.
- The site carries **no images**. Every page has an `icon` in its frontmatter
  and every `<Card>` has an `icon`; icons are Font Awesome names (the Mintlify
  starter default, so `icons.library` stays unset). Do not add `<img>`,
  `<Frame>`, markdown images, or an `image:` field.
- Navigation is `navigation.tabs`: one tab per application (Get started, Chat,
  Code, Bot, CLI, Design, Security, Reference), each tab a list of groups, each
  tab and group with an icon. Every product tab opens on its hub page
  (`<product>/index.mdx`). Do not add a second overview page beside a hub.
- Every page has a unique `title`, a `description` under 160 characters, and a
  closing **Related** section. Where a sidebar label differs from the title,
  set `sidebarTitle` and add the alternative name to `keywords`.
- Keep every navigation slug, footer link, redirect destination, and internal
  href backed by a page, and every problem page's `type` URL on
  `https://docs.cortex.foundation/problems/{code}`.
- Only document API paths on `reference/errors`, `bounty/public-api`, and the
  problem pages, and only paths the backend router registers.
- Run `node scripts/check-docs-site.mjs`,
  `bash scripts/tests/check-docs-site.test.sh`,
  `node scripts/tests/docs-ui.test.mjs`, then
  `npm exec --yes --package=mint@4.2.876 -- mint validate` before committing.
- For error-code or endpoint changes, also run the checker with a backend
  checkout as its first argument. Coordinate the two PRs; the backend owns the
  API contract and checks this repository in its CI.
- Do not change the Mintlify integration, custom domain, or DNS without an
  explicit request.
