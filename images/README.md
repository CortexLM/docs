# Icon, card, and frame slots

Paper lock boards use **doodle** card art: cream paper, ink line, brand green
`#1F4945`, a small leaf on several marks.

Frame illustrations sit on a cream–green wallpaper with **matte ink** macOS or
terminal chrome: dual hairlines, traffic lights, and a green focus ring.
No violet. No cyan. Green is focus and frame only — never a filled meadow CTA.

CLI canon from `CortexLM/cli` `docs/media/` is vendored under `cli/`.

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
| `frames/*.svg` | macOS / terminal window illustrations for guides |
| `cli/intro.gif` | CLI desktop demo (vendored from CortexLM/cli) |
| `cli/macos-wallpaper-green.jpg` | Forest wallpaper used in CLI frames |
| `cli/splash.png` `cli/working.png` | Intro-preview stills (vendored) |

Regenerate SVG frames with `python3 scripts/generate-docs-frames.py`.
Home, Chat hub, and Get started cards use the `doodle-*` paths.
