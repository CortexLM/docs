# Icon, card, and product media

Paper lock boards use **doodle** card art: cream paper, ink line, brand green
`#1F4945`, a small leaf on several marks. Doodles are icons, not product UI.

Guide heroes that depict the product must be a **real Cortex surface**:

- `product/*.png` — staging screenshot hooks (`chat-home.png`,
  `chat-session.png`, `code-home.png`, `bot-home.png`). Overwrite in place.
- `cli/` — vendored from CortexLM/cli `docs/media/` (GIF, wallpaper, terminal stills).

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
| `icon-api.svg` `icon-cli.svg` `icon-desktop.svg` | Secondary slots, not on the home grid |
| `product/chat-home.png` | Chat home hook (staging PNG pending) |
| `product/chat-session.png` | Chat session hook (staging PNG pending) |
| `product/code-home.png` | Code home hook (staging PNG pending) |
| `product/bot-home.png` | Bot home hook (staging PNG pending) |
| `cli/intro.gif` | CLI desktop demo (vendored from CortexLM/cli) |
| `cli/macos-wallpaper-green.jpg` | Forest wallpaper used in CLI frames |
| `cli/splash.png` `cli/working.png` `cli/composer.png` | Intro-preview stills (vendored) |
| `cli/model.png` `cli/palette.png` `cli/shell.png` | Extra CLI stills (vendored) |

Home, Chat hub, and Get started cards use the `doodle-*` paths.
Green is focus and frame only — never a filled meadow CTA. No violet.
