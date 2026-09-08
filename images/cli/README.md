# CLI canon media

Vendored from [`CortexLM/cli`](https://github.com/CortexLM/cli). Real renders of
the shipped TUI — not SVG mocks, not invented terminal art. Each file is used on
exactly one page; no two files share a sha256.

## `intro.gif`

`docs/media/intro.gif` — the README demo: the signed lock TUI composited onto a
photographed macOS desktop. Generated, not a live recording. Used on `cli/index`.

## `runtime/` — Designer cli pack

Headless `MockTerminal` renders of the live session chrome at 120×40, vendored
from `docs/media/tui-lock-v2/runtime/120x40/` at CortexLM/cli `4d41ef36`
(`[feat] /goal persisted long-horizon workflows (#54)`). Inky background,
dual-hairline composer, model chip on the border, accent `#1F4945`. The full pack
is 82 boards; these are the ones the guides use.

| File | State | Used on |
| --- | --- | --- |
| `composer-hover.png` | Session composer, pointer hovering | `cli/index` |
| `welcome-cortex.png` | Welcome splash v0.1.10, empty composer | `cli/install` |
| `login.png` | Sign-in picker: browser or API key | `cli/sign-in` |
| `login-waiting.png` | Waiting for browser, device code shown | `cli/sign-in` |
| `first-run-tips.png` | Welcome plus the first-run tips panel | `cli/quickstart` |
| `session-thinking-live.png` | Thinking · 3s, follow-up composer | `cli/quickstart` |
| `composer-empty.png` | Empty Agent composer | `cli/tui` |
| `composer-typing.png` | Composer with a prompt being typed | `cli/tui` |
| `tool-tiles.png` | Grouped Read / Grep / Shell tool rows | `cli/tui` |
| `diff-hunk.png` | Edit tile with a unified diff | `cli/tui` |
| `queue.png` | Two queued follow-ups behind a running Shell | `cli/tui` |
| `interrupt-stopped.png` | × Stopped after Esc | `cli/tui` |
| `cloud-handoff.png` | `&` hand-off to Cortex Cloud | `cli/tui` |
| `slash-palette.png` | Slash palette home, `/goal` after `/plan` | `cli/slash-commands` |
| `slash-model-typed.png` | Palette filtered by `/model` | `cli/slash-commands` |
| `usage.png` | `/usage` meters | `cli/slash-commands` |
| `mode-plan.png` | Plan mode, drafted plan, Plan · no edits composer | `cli/modes-and-permissions` |
| `plan-confirm.png` | Implement this plan? picker | `cli/modes-and-permissions` |
| `permission-prompt.png` | Inline approval, four numbered options | `cli/modes-and-permissions` |
| `permissions-picker.png` | `/permissions`: Smart, Read-only, Full access | `cli/modes-and-permissions` |
| `sandbox-deny.png` | × Sandbox denied with three options | `cli/modes-and-permissions` |
| `model-effort-medium.png` | `/model` effort radios, Medium selected | `cli/modes-and-permissions` |
| `goal-chip-active.png` | Composer chip Goal · 2/8 | `cli/goal` |
| `goal-chip-done.png` | Composer chip Goal · done | `cli/goal` |
| `resume-picker.png` | `/resume` session picker | `cli/sessions` |
| `clear-confirm.png` | `/clear` confirmation | `cli/sessions` |
| `shortcuts-overlay.png` | Ctrl+X shortcuts overlay | `cli/keyboard` |
| `config-tree.png` | `/config` read-only tree | `cli/configuration` |
| `settings-appearance.png` | `/settings` → Appearance | `cli/configuration` |
| `mcp-servers.png` | `/mcp` server manager | `cli/extend` |
| `skills.png` | `/skills` picker | `cli/extend` |
| `plugins.png` | `/plugins` manager | `cli/extend` |
| `error-unavailable.png` | The coding service is temporarily unavailable | `cli/troubleshooting` |
| `quota-exhausted.png` | × Agent quota exhausted, held composer | `cli/troubleshooting` |
| `diagnostics.png` | Diagnostics row after an edit | `cli/troubleshooting` |

Refresh from the CLI repository rather than editing pixels here. When a new state
is needed, take the matching board from the pack (`docs/media/tui-lock-v2/runtime/`)
and add a row above. Not vendored on purpose: `login-success.png` (shows a real
account address). The earlier macOS-desktop composites (`splash`, `working`,
`composer`, `model`, `palette`, `shell`) were retired in favour of this pack.
