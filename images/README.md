# Icon, card, and product media

Paper lock boards use **doodle** card art: cream paper, ink line, brand green
`#1F4945`, a small leaf on several marks. Doodles are icons, not product UI.

Guide heroes that depict the product are **real Cortex screenshots**:

- `product/*.png` — live Chat / Code / Bot / Connectors captures
- `cli/` — vendored from CortexLM/cli `docs/media/` (GIF, wallpaper, terminal stills)

Do not add abstract product-window SVGs. `frames/*.svg` is retired.

| File | Slot |
| --- | --- |
| `doodle-getting-started.svg` | Open book, compass, leaf |
| `doodle-chat.svg` | Overlapping speech bubbles, leaf |
| `doodle-code.svg` | Editor frame, `< \| >` |
| `doodle-bot.svg` | Robot head, green gear |
| `doodle-design.svg` | Framed canvas, pencil, leaf |
| `doodle-security.svg` | Shield, lock, vine |
| `doodle-changelog.svg` | Notebook, up arrows |
| `icon-*.svg` | Same art, kept for older `icon-*` references |
| `card-chat.svg` … `card-design.svg` | How-it-works illustrations (same doodles) |
| `product/chat-home.png` | Chat home |
| `product/chat-session.png` | Chat session |
| `product/code-home.png` | Code guest gate |
| `product/bot-home.png` | Bot guest gate |
| `product/design-home.png` | Connectors / Customize |
| `cli/intro.gif` | CLI desktop demo (vendored from CortexLM/cli) |
| `cli/macos-wallpaper-green.jpg` | Forest wallpaper used in CLI frames |
| `cli/splash.png` `cli/working.png` `cli/composer.png` | Intro-preview stills (vendored) |

Home, Chat hub, and Get started cards use the `doodle-*` paths.
Green is focus and frame only — never a filled meadow CTA. No violet.
