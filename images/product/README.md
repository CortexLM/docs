# Product screenshots

Live Cortex app captures (1280×800, guest session unless noted) taken from
`cortex.foundation` with headless Chrome. These are the product heroes. Do
not replace them with SVG mocks or marked placeholders, and do not reuse one
capture on more than one page — every guide shows a distinct surface.

Cream / ink / `#1F4945` stay on site chrome. The pixels are the app.

## Chat

| File | Surface | Used on |
| --- | --- | --- |
| `chat-home.png` | Chat home, empty guest session | `getting-started/quickstart` |
| `chat-home-recents.png` | Chat home with Recents populated | `index` |
| `chat-home-dark.png` | Chat home, Dark theme | `chat/index` |
| `chat-home-fr.png` | Chat home, French interface | `getting-started/what-is-cortex` |
| `chat-session.png` | A thread with a one-paragraph reply | `chat/overview` |
| `chat-composer-typed.png` | A multi-line prompt typed in the composer | `chat/quickstart` |
| `chat-composer-menu.png` | The composer `+` menu: Attach file, Image, Check origin | `chat/images` |
| `chat-model-picker.png` | Model chip open: models, Thinking, Deep Research | `chat/models` |
| `chat-deep-research.png` | Research card prefill with Deep Research on | `chat/deep-research` |
| `chat-streaming.png` | A turn in flight — “Cortex is responding…” | `chat/streaming` |
| `chat-reply-headings.png` | A finished reply with headings | `chat/how-it-works` |
| `chat-reply-code.png` | A reply with a Python code block, Copy and Listen | `chat/voice` |
| `chat-canvas-document.png` | A new chat with a document canvas open | `chat/canvases` |
| `chat-projects.png` | Projects, empty state | `chat/projects` |
| `chat-new-project.png` | New project dialog | `chat/projects` |
| `chat-move-to-project.png` | Move to project popover on a thread | `chat/projects` |
| `chat-library.png` | Library, empty state with type filters | `chat/library` |
| `chat-planning.png` | Planning, empty state with filters | `chat/plans` |
| `chat-start-plan.png` | Start a plan from this chat | `chat/plans` |
| `chat-new-plan.png` | New plan dialog | `chat/plans` |
| `chat-connectors.png` | Customize → Connectors | `chat/tools` |

## Settings and account

| File | Surface | Used on |
| --- | --- | --- |
| `accounts-sign-in.png` | The sign-in dialog | `getting-started/accounts` |
| `settings-general.png` | Settings → General | `getting-started/settings` |
| `settings-shortcuts.png` | Settings → General, keyboard shortcuts | `getting-started/settings` |
| `settings-models.png` | Settings → Models | `chat/models` |
| `settings-integrations.png` | Settings → Integrations, Connect GitHub | `code/github` |
| `settings-mcp-servers.png` | Settings → Integrations, MCP servers | `chat/tools` |
| `settings-data-privacy.png` | Settings → Data & privacy, top | `security/overview` |
| `settings-memory.png` | Settings → Data & privacy, Memory and Your data | `chat/memory` |
| `settings-plans.png` | Settings → Plan & billing, plan cards | `getting-started/plans` |
| `settings-plan-usage.png` | Settings → Plan & billing, guest usage | `getting-started/plans` |
| `privacy-cookie-banner.png` | Cookie consent banner on first visit | `security/overview` |

## Code, Bot, Security, Foundation

| File | Surface | Used on |
| --- | --- | --- |
| `code-public.png` | `cortex.foundation/code` public page | `code/index` |
| `code-public-features.png` | Same page, feature grid | `code/overview` |
| `code-home.png` | Code guest gate (“This space is reserved”) | `code/quickstart` |
| `bot-public.png` | `cortex.foundation/bot` public page | `bot/index` |
| `bot-public-features.png` | Same page, feature grid | `bot/overview` |
| `bot-home.png` | Bot guest gate | `bot/quickstart` |
| `security-public.png` | `cortex.foundation/security` public page | `code/security` |
| `security-public-features.png` | Same page, feature grid | `code/security` |
| `news-announcement.png` | News: Chat, Code, and Bot are live | `changelog` |
| `about.png` | `cortex.foundation/about` | `getting-started/what-is-cortex` |

## Not yet captured

Member-only surfaces have no guest capture and their pages ship without a
product frame until one lands: a Code session timeline in the web app, the
Bot setup form and Computer rail, a Design canvas in the desktop app, the
Bot desktop app. Capture them from a signed-in staging account at 1280×800
and add a row above; never substitute an SVG mock.

CLI stills live in `images/cli/` (vendored from CortexLM/cli).
