# Icon, card, and product media

Section tops and home cards use **banner** illustrations: cream paper, ink
line, brand green `#1F4945`. Banners are heroes and Mintlify `Card img`
slots, not product UI. Doodles remain as small icon stand-ins.

Guide heroes that depict the product are **real Cortex screenshots**:

- `banners/*.png` — section / home cards (Chat, Code, Bot, Security, …)
- `product/*.png` — live Chat / Code / Bot / Settings / public-page captures, one per guide
- `cli/` — vendored from CortexLM/cli: the README GIF and the CLI runtime pack (`cli/runtime/`)

Do not add abstract product-window SVGs. `frames/*.svg` and
`scripts/generate-docs-frames.py` are retired and removed.
Do not add Ask Assistant chrome or pixel plates. Never show the same
product capture on two pages; capture the surface instead.

| File | Slot |
| --- | --- |
| `banners/getting-started.png` | Home / Get started card |
| `banners/chat.png` | Chat hub + Chat quickstart card |
| `banners/code.png` | Code hub card |
| `banners/bot.png` | Bot hub card |
| `banners/security.png` | Security hero |
| `banners/changelog.png` | Changelog hero |
| `doodle-getting-started.svg` | Open book, compass, leaf |
| `doodle-chat.svg` | Overlapping speech bubbles, leaf |
| `doodle-code.svg` | Editor frame, `< \| >` |
| `doodle-bot.svg` | Robot head, green gear |
| `doodle-security.svg` | Shield, lock, vine |
| `doodle-changelog.svg` | Notebook, up arrows |
| `icon-*.svg` | Same art, kept for older `icon-*` references |
| `card-chat.svg` … `card-bot.svg` | How-it-works illustrations (same doodles) |
| `product/*.png` | Live app captures, one distinct surface per page — see `product/README.md` |
| `cli/intro.gif` | CLI desktop demo (vendored from CortexLM/cli) |
| `cli/runtime/*.png` | CLI runtime pack — one distinct TUI state per frame, see `cli/README.md` |

Home, Chat hub, Get started, and other section cards use the `banners/*`
paths. Green is focus and frame only — never a filled meadow CTA. No violet.

There is no Design asset set: Design is not a public product vertical, so no
page carries a Design banner, doodle, icon, or card.

