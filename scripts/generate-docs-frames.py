#!/usr/bin/env python3
"""Generate macOS + terminal frame illustrations for Cortex docs.

Tokens: cream #FAF8F4 · ink #211F1C · green #1F4945 (focus / frame only).
Chrome: matte ink, dual hairlines, green focus. No violet, no cyan.
"""

from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "images" / "frames"

CREAM = "#FAF8F4"
INK = "#211F1C"
GREEN = "#1F4945"
RAIL = "#F3F0EA"
LINE = "#E3DFD7"
MUTED = "#6E6A62"
DARK = "#161412"
PANEL = "#1A1815"
HAIR = "#3A3A3A"
SELECT = "#E1E5DE"


def wallpaper(w: int = 960, h: int = 560) -> str:
    trees = []
    for i, (x, y, r) in enumerate(
        ((80, 430, 90), (180, 410, 70), (300, 440, 110), (720, 420, 95), (860, 400, 80))
    ):
        trees.append(
            f'<ellipse cx="{x}" cy="{y}" rx="{r}" ry="{int(r * 0.72)}" fill="{GREEN}" opacity="{0.18 + (i % 3) * 0.04}"/>'
        )
    return f"""
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#D7E4DC"/>
      <stop offset="0.55" stop-color="#EFE8DC"/>
      <stop offset="1" stop-color="#C4D0C4"/>
    </linearGradient>
    <radialGradient id="mist" cx="50%" cy="70%" r="60%">
      <stop offset="0" stop-color="{CREAM}" stop-opacity="0.35"/>
      <stop offset="1" stop-color="{GREEN}" stop-opacity="0.12"/>
    </radialGradient>
  </defs>
  <rect width="{w}" height="{h}" fill="url(#sky)"/>
  <rect width="{w}" height="{h}" fill="url(#mist)"/>
  <path d="M0 360 C120 320 220 390 360 350 C500 310 620 390 960 330 L960 {h} L0 {h} Z" fill="{GREEN}" opacity="0.22"/>
  <path d="M0 400 C160 360 280 430 480 390 C680 350 780 430 960 380 L960 {h} L0 {h} Z" fill="{INK}" opacity="0.16"/>
  {"".join(trees)}
"""


def traffic(x: int, y: int) -> str:
    return f"""
    <circle cx="{x}" cy="{y}" r="5" fill="#C4B8A8"/>
    <circle cx="{x + 16}" cy="{y}" r="5" fill="#C4B8A8"/>
    <circle cx="{x + 32}" cy="{y}" r="5" fill="{GREEN}"/>
"""


def macos_window(
    x: int,
    y: int,
    w: int,
    h: int,
    title: str,
    focused: bool = True,
    dark: bool = False,
) -> tuple[str, int, int, int, int]:
    """Return (svg, content_x, content_y, content_w, content_h)."""
    fill = DARK if dark else CREAM
    title_fill = PANEL if dark else RAIL
    title_ink = CREAM if dark else INK
    ring = (
        f'<rect x="{x - 3}" y="{y - 3}" width="{w + 6}" height="{h + 6}" rx="16" fill="none" stroke="{GREEN}" stroke-width="2"/>'
        if focused
        else ""
    )
    chrome = f"""
  {ring}
  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="13" fill="{fill}"/>
  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="13" fill="none" stroke="{INK}" stroke-width="1.5"/>
  <rect x="{x + 2}" y="{y + 2}" width="{w - 4}" height="{h - 4}" rx="11" fill="none" stroke="{LINE if not dark else HAIR}" stroke-width="1"/>
  <rect x="{x}" y="{y}" width="{w}" height="36" rx="13" fill="{title_fill}"/>
  <rect x="{x}" y="{y + 24}" width="{w}" height="12" fill="{title_fill}"/>
  <path d="M{x} {y + 36} H{x + w}" stroke="{INK if not dark else HAIR}" stroke-width="1"/>
  <path d="M{x} {y + 37} H{x + w}" stroke="{LINE if not dark else "#2A2824"}" stroke-width="1"/>
  {traffic(x + 18, y + 18)}
  <text x="{x + w / 2}" y="{y + 23}" text-anchor="middle" font-family="Inter, ui-sans-serif, sans-serif" font-size="12" font-weight="600" fill="{title_ink}">{title}</text>
"""
    return chrome, x + 12, y + 48, w - 24, h - 60


def terminal_window(x: int, y: int, w: int, h: int, title: str) -> tuple[str, int, int, int, int]:
    return macos_window(x, y, w, h, title, focused=True, dark=True)


def text(x, y, s, *, size=13, fill=INK, weight=500, family="Inter, ui-sans-serif, sans-serif", anchor="start"):
    return (
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{family}" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}">{s}</text>'
    )


def mono(x, y, s, *, size=12, fill=CREAM, weight=500):
    return text(
        x,
        y,
        s,
        size=size,
        fill=fill,
        weight=weight,
        family="IBM Plex Mono, ui-monospace, monospace",
    )


def wrap(body: str, w: int = 960, h: int = 560, label: str = "Cortex") -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none" role="img" aria-label="{label}">
{wallpaper(w, h)}
{body}
</svg>
'''


def switcher() -> str:
    chrome, cx, cy, cw, ch = macos_window(90, 70, 780, 420, "Cortex — cortex.foundation")
    main = cx + 184
    pills = []
    for i, (name, on) in enumerate((("Chat", True), ("Code", False), ("Bot", False))):
        px = main + 16 + i * 88
        bg = SELECT if on else "transparent"
        ink = GREEN if on else MUTED
        bar = f'<rect x="{px}" y="{cy + 8}" width="72" height="28" rx="7" fill="{bg}"/>'
        if on:
            bar += f'<rect x="{px}" y="{cy + 8}" width="3" height="28" rx="1.5" fill="{GREEN}"/>'
        pills.append(bar + text(px + 36, cy + 27, name, size=13, fill=ink, weight=600, anchor="middle"))
    composer = f'''
  <rect x="{main + 16}" y="{cy + ch - 72}" width="{cx + cw - main - 40}" height="56" rx="12" fill="{RAIL}" stroke="{INK}" stroke-width="1"/>
  <rect x="{main + 18}" y="{cy + ch - 70}" width="{cx + cw - main - 44}" height="52" rx="10" fill="none" stroke="{LINE}" stroke-width="1"/>
  {text(main + 36, cy + ch - 38, "Ask Cortex anything…", size=14, fill=MUTED)}
  <rect x="{cx + cw - 70}" y="{cy + ch - 58}" width="46" height="28" rx="8" fill="{INK}"/>
  {text(cx + cw - 47, cy + ch - 39, "Send", size=11, fill=CREAM, weight=600, anchor="middle")}
'''
    bubbles = f'''
  <rect x="{main + 16}" y="{cy + 52}" width="280" height="44" rx="12" fill="{RAIL}"/>
  {text(main + 32, cy + 79, "What can Cortex Chat do?", size=13, fill=INK)}
  <rect x="{main + 16}" y="{cy + 108}" width="420" height="68" rx="12" fill="{CREAM}" stroke="{LINE}" stroke-width="1"/>
  {text(main + 32, cy + 134, "Projects, documents, research, and pictures —", size=13, fill=INK)}
  {text(main + 32, cy + 156, "before you sign in. Code and Bot need an account.", size=13, fill=INK)}
'''
    sidebar = f'''
  <rect x="{cx}" y="{cy}" width="168" height="{ch}" fill="{RAIL}"/>
  <path d="M{cx + 168} {cy} V{cy + ch}" stroke="{LINE}" stroke-width="1"/>
  {text(cx + 16, cy + 28, "New chat", size=12, fill=INK, weight=600)}
  {text(cx + 16, cy + 56, "Projects", size=11, fill=MUTED, weight=600)}
  <rect x="{cx + 10}" y="{cy + 68}" width="148" height="28" rx="7" fill="{SELECT}"/>
  {text(cx + 22, cy + 87, "Launch notes", size=12, fill=GREEN, weight=600)}
  {text(cx + 22, cy + 118, "Research brief", size=12, fill=MUTED)}
  {text(cx + 22, cy + 146, "Image drafts", size=12, fill=MUTED)}
'''
    return wrap(
        chrome
        + sidebar
        + "".join(pills)
        + bubbles
        + composer,
        label="Cortex product switcher in a macOS window",
    )


def chat_composer() -> str:
    chrome, cx, cy, cw, ch = macos_window(80, 64, 800, 432, "Cortex Chat")
    return wrap(
        chrome
        + f'''
  <rect x="{cx}" y="{cy}" width="200" height="{ch}" fill="{RAIL}"/>
  <path d="M{cx + 200} {cy} V{cy + ch}" stroke="{LINE}"/>
  {text(cx + 16, cy + 24, "New chat", size=13, fill=INK, weight=600)}
  {text(cx + 16, cy + 54, "TODAY", size=10, fill=MUTED, weight=600)}
  <rect x="{cx + 10}" y="{cy + 66}" width="180" height="30" rx="7" fill="{SELECT}"/>
  <rect x="{cx + 10}" y="{cy + 66}" width="3" height="30" fill="{GREEN}"/>
  {text(cx + 24, cy + 86, "First conversation", size=12, fill=GREEN, weight=600)}
  {text(cx + 24, cy + 122, "Attach a brief", size=12, fill=MUTED)}
  <rect x="{cx + 220}" y="{cy + 16}" width="{cw - 236}" height="220" rx="10" fill="{CREAM}" stroke="{LINE}"/>
  {text(cx + 240, cy + 48, "You", size=11, fill=MUTED, weight=600)}
  {text(cx + 240, cy + 72, "Summarize this launch brief for the team.", size=14, fill=INK)}
  {text(cx + 240, cy + 110, "Cortex", size=11, fill=GREEN, weight=600)}
  {text(cx + 240, cy + 134, "Three outcomes, two risks, one open question.", size=14, fill=INK)}
  {text(cx + 240, cy + 158, "I used the attached brief — not a pasted URL.", size=13, fill=MUTED)}
  <rect x="{cx + 220}" y="{cy + ch - 78}" width="{cw - 236}" height="64" rx="12" fill="{RAIL}" stroke="{INK}" stroke-width="1.2"/>
  <rect x="{cx + 222}" y="{cy + ch - 76}" width="{cw - 240}" height="60" rx="10" fill="none" stroke="{LINE}"/>
  {text(cx + 240, cy + ch - 40, "Ask a follow-up, or attach another Library file…", size=13, fill=MUTED)}
  <rect x="{cx + cw - 86}" y="{cy + ch - 62}" width="54" height="28" rx="8" fill="{INK}"/>
  {text(cx + cw - 59, cy + ch - 43, "Send", size=11, fill=CREAM, weight=600, anchor="middle")}
''',
        label="Cortex Chat composer in a macOS window",
    )


def chat_projects() -> str:
    chrome, cx, cy, cw, ch = macos_window(70, 60, 820, 440, "Chat · Projects")
    return wrap(
        chrome
        + f'''
  <rect x="{cx}" y="{cy}" width="220" height="{ch}" fill="{RAIL}"/>
  {text(cx + 16, cy + 28, "Projects", size=14, fill=INK, weight=600)}
  <rect x="{cx + 12}" y="{cy + 44}" width="196" height="36" rx="8" fill="{SELECT}"/>
  <rect x="{cx + 12}" y="{cy + 44}" width="3" height="36" fill="{GREEN}"/>
  {text(cx + 28, cy + 67, "Launch notes", size=13, fill=GREEN, weight=600)}
  {text(cx + 28, cy + 112, "Research brief", size=13, fill=MUTED)}
  {text(cx + 28, cy + 144, "Image drafts", size=13, fill=MUTED)}
  {text(cx + 248, cy + 28, "Launch notes", size=16, fill=INK, weight=600)}
  {text(cx + 248, cy + 52, "Threads and Library files stay in this folder.", size=13, fill=MUTED)}
  <rect x="{cx + 248}" y="{cy + 72}" width="260" height="88" rx="10" fill="{CREAM}" stroke="{LINE}"/>
  {text(cx + 264, cy + 100, "Thread", size=11, fill=MUTED, weight=600)}
  {text(cx + 264, cy + 124, "Outline the September launch", size=13, fill=INK)}
  <rect x="{cx + 524}" y="{cy + 72}" width="260" height="88" rx="10" fill="{CREAM}" stroke="{LINE}"/>
  {text(cx + 540, cy + 100, "Library", size=11, fill=MUTED, weight=600)}
  {text(cx + 540, cy + 124, "brief.pdf  ·  pinned", size=13, fill=INK)}
  <rect x="{cx + 248}" y="{cy + 176}" width="536" height="160" rx="10" fill="{RAIL}"/>
  {text(cx + 268, cy + 210, "A project is a folder plus its chats —", size=14, fill=INK)}
  {text(cx + 268, cy + 234, "not a second selected pill in the sidebar.", size=14, fill=INK)}
  {text(cx + 268, cy + 270, "Memory is account-scoped. Design canvases are a different object.", size=13, fill=MUTED)}
''',
        label="Chat projects folder in a macOS window",
    )


def chat_research() -> str:
    chrome, cx, cy, cw, ch = macos_window(80, 56, 800, 448, "Chat · Deep Research")
    return wrap(
        chrome
        + f'''
  {text(cx + 8, cy + 20, "Stay in Chat  ·  plan, then run", size=12, fill=MUTED, weight=600)}
  <rect x="{cx}" y="{cy + 36}" width="{cw}" height="120" rx="10" fill="{RAIL}"/>
  {text(cx + 20, cy + 68, "Research plan", size=13, fill=INK, weight=600)}
  {text(cx + 20, cy + 94, "1. What shipped in Cortex Chat this month?", size=13, fill=INK)}
  {text(cx + 20, cy + 118, "2. Which sources should we trust?", size=13, fill=INK)}
  <rect x="{cx + cw - 120}" y="{cy + 56}" width="96" height="32" rx="8" fill="{INK}"/>
  {text(cx + cw - 72, cy + 77, "Start", size=13, fill=CREAM, weight=600, anchor="middle")}
  <rect x="{cx}" y="{cy + 172}" width="240" height="180" rx="10" fill="{CREAM}" stroke="{LINE}"/>
  {text(cx + 16, cy + 200, "Questions", size=12, fill=MUTED, weight=600)}
  {text(cx + 16, cy + 228, "Up to 32", size=18, fill=INK, weight=600)}
  {text(cx + 16, cy + 256, "8 in parallel", size=13, fill=MUTED)}
  <rect x="{cx + 256}" y="{cy + 172}" width="240" height="180" rx="10" fill="{CREAM}" stroke="{LINE}"/>
  {text(cx + 272, cy + 200, "Sources", size=12, fill=MUTED, weight=600)}
  {text(cx + 272, cy + 228, "Up to 80", size=18, fill=INK, weight=600)}
  {text(cx + 272, cy + 256, "4 fetches each", size=13, fill=MUTED)}
  <rect x="{cx + 512}" y="{cy + 172}" width="264" height="180" rx="10" fill="{CREAM}" stroke="{LINE}"/>
  {text(cx + 528, cy + 200, "Not a Code tool", size=12, fill=MUTED, weight=600)}
  {text(cx + 528, cy + 228, "Chat turn only", size=18, fill=INK, weight=600)}
  {text(cx + 528, cy + 256, "Code refuses research.", size=13, fill=MUTED)}
''',
        label="Deep Research plan in a macOS window",
    )


def chat_images() -> str:
    chrome, cx, cy, cw, ch = macos_window(90, 70, 780, 420, "Chat · Cortex-Image-1")
    return wrap(
        chrome
        + f'''
  <rect x="{cx}" y="{cy}" width="{cw * 0.46}" height="{ch}" rx="10" fill="{RAIL}"/>
  {text(cx + 20, cy + 36, "Improving prompt…", size=13, fill=MUTED)}
  <rect x="{cx + 20}" y="{cy + 56}" width="{cw * 0.46 - 40}" height="{ch - 80}" rx="8" fill="{CREAM}" stroke="{LINE}"/>
  <path d="M{cx + 70} {cy + 220} C{cx + 110} {cy + 160}, {cx + 160} {cy + 250}, {cx + 220} {cy + 180}" stroke="{GREEN}" stroke-width="3" fill="none"/>
  <circle cx="{cx + 90}" cy="{cy + 140}" r="18" fill="{GREEN}" opacity="0.35"/>
  {text(cx + cw * 0.46 + 24, cy + 40, "generate_image", size=12, fill=MUTED, weight=600)}
  {text(cx + cw * 0.46 + 24, cy + 72, "A complete English scene", size=16, fill=INK, weight=600)}
  {text(cx + cw * 0.46 + 24, cy + 104, "queued → generating → Library file", size=13, fill=MUTED)}
  {text(cx + cw * 0.46 + 24, cy + 148, "Size, optional seed, steps 1–50", size=13, fill=INK)}
  {text(cx + cw * 0.46 + 24, cy + 176, "Free and Guest: images_per_day quota", size=13, fill=INK)}
  {text(cx + cw * 0.46 + 24, cy + 216, "Built on NVIDIA Cosmos", size=12, fill=MUTED)}
  {text(cx + cw * 0.46 + 24, cy + 248, "Empty cluster URL fails closed", size=12, fill=MUTED)}
  {text(cx + cw * 0.46 + 24, cy + 276, "before any quota is spent.", size=12, fill=MUTED)}
''',
        label="Image generation card in a macOS window",
    )


def code_session() -> str:
    chrome, cx, cy, cw, ch = macos_window(70, 56, 820, 448, "Cortex Code · session")
    modes = ""
    for i, (name, on) in enumerate((("Ask", False), ("Plan", False), ("Agent", True))):
        px = cx + 220 + i * 92
        bg = SELECT if on else CREAM
        ink = GREEN if on else MUTED
        modes += f'<rect x="{px}" y="{cy + 12}" width="84" height="28" rx="8" fill="{bg}" stroke="{LINE}"/>'
        modes += text(px + 42, cy + 31, name, size=12, fill=ink, weight=600, anchor="middle")
    return wrap(
        chrome
        + modes
        + f'''
  <rect x="{cx}" y="{cy}" width="200" height="{ch}" fill="{RAIL}"/>
  {text(cx + 16, cy + 28, "Timeline", size=12, fill=MUTED, weight=600)}
  {text(cx + 16, cy + 56, "You  ·  add /healthz + test", size=12, fill=INK)}
  {text(cx + 16, cy + 84, "read  src/router.rs", size=12, fill=MUTED)}
  {text(cx + 16, cy + 112, "edit  src/router.rs", size=12, fill=INK)}
  {text(cx + 16, cy + 140, "bash  cargo test", size=12, fill=MUTED)}
  <rect x="{cx + 216}" y="{cy + 56}" width="{cw - 216}" height="200" rx="10" fill="{CREAM}" stroke="{LINE}"/>
  {text(cx + 236, cy + 88, "Agent can change the repository.", size=14, fill=INK, weight=600)}
  {text(cx + 236, cy + 116, "Ask and Plan do not edit files or run shell.", size=13, fill=MUTED)}
  {text(cx + 236, cy + 148, "Stop cancels the live turn. A follow-up can pick", size=13, fill=INK)}
  {text(cx + 236, cy + 172, "a different mode. Web Code has no model picker.", size=13, fill=INK)}
  <rect x="{cx + 216}" y="{cy + 272}" width="{cw - 216}" height="88" rx="10" fill="{DARK}"/>
  {mono(cx + 236, cy + 308, "$ cargo test healthz", size=13, fill=CREAM)}
  {mono(cx + 236, cy + 332, "ok   healthz_returns_200", size=13, fill="#8AC5B9")}
''',
        label="Code session timeline in a macOS window",
    )


def code_cloud() -> str:
    chrome, cx, cy, cw, ch = macos_window(90, 70, 780, 420, "Cortex Code · Cloud guest")
    return wrap(
        chrome
        + f'''
  <rect x="{cx}" y="{cy}" width="{cw / 2 - 10}" height="{ch}" rx="10" fill="{RAIL}"/>
  {text(cx + 20, cy + 40, "Cloud guest", size=16, fill=INK, weight=600)}
  {text(cx + 20, cy + 72, "Isolated Firecracker machine", size=13, fill=MUTED)}
  {text(cx + 20, cy + 112, "read_file   write_file   edit_file", size=13, fill=INK)}
  {text(cx + 20, cy + 140, "glob   grep   bash   todos", size=13, fill=INK)}
  {text(cx + 20, cy + 180, "Headless — no desktop", size=13, fill=MUTED)}
  {text(cx + 20, cy + 208, "Not Chat’s Python sandbox", size=13, fill=MUTED)}
  <rect x="{cx + cw / 2 + 10}" y="{cy}" width="{cw / 2 - 10}" height="{ch}" rx="10" fill="{DARK}"/>
  {mono(cx + cw / 2 + 32, cy + 48, "prepare repository", fill="#8AC5B9")}
  {mono(cx + cw / 2 + 32, cy + 76, "attach guest")}
  {mono(cx + cw / 2 + 32, cy + 104, "snapshot ready")}
  {mono(cx + cw / 2 + 32, cy + 148, "This PC / SSH", fill="#B0AAA0")}
  {mono(cx + cw / 2 + 32, cy + 176, "desktop app and CLI only", fill="#B0AAA0")}
  {mono(cx + cw / 2 + 32, cy + 220, "no Secrets page", fill="#B0AAA0")}
''',
        label="Code Cloud guest in a macOS window",
    )


def bot_computer() -> str:
    chrome, cx, cy, cw, ch = macos_window(60, 52, 840, 456, "Cortex Bot · Computer")
    return wrap(
        chrome
        + f'''
  <rect x="{cx}" y="{cy}" width="{cw * 0.58}" height="{ch}" fill="{RAIL}"/>
  {text(cx + 20, cy + 32, "Finch", size=16, fill=INK, weight=600)}
  {text(cx + 20, cy + 56, "Conversation", size=12, fill=MUTED)}
  <rect x="{cx + 16}" y="{cy + 76}" width="{cw * 0.58 - 32}" height="56" rx="10" fill="{CREAM}"/>
  {text(cx + 32, cy + 110, "Open the weekly report and summarise it.", size=13, fill=INK)}
  <rect x="{cx + 16}" y="{cy + 148}" width="{cw * 0.58 - 32}" height="56" rx="10" fill="{CREAM}" stroke="{LINE}"/>
  {text(cx + 32, cy + 182, "Opening desktop… then I will take a screenshot.", size=13, fill=INK)}
  <rect x="{cx + cw * 0.58 + 8}" y="{cy}" width="{cw * 0.42 - 8}" height="{ch}" fill="{DARK}"/>
  {text(cx + cw * 0.58 + 24, cy + 32, "Computer", size=13, fill=CREAM, weight=600)}
  {text(cx + cw * 0.58 + 24, cy + 56, "Cloud  ·  live desktop", size=11, fill="#B0AAA0")}
  <rect x="{cx + cw * 0.58 + 20}" y="{cy + 76}" width="{cw * 0.42 - 40}" height="200" rx="8" fill="#111110" stroke="{GREEN}" stroke-width="2"/>
  <rect x="{cx + cw * 0.58 + 36}" y="{cy + 96}" width="120" height="16" rx="3" fill="{HAIR}"/>
  <rect x="{cx + cw * 0.58 + 36}" y="{cy + 124}" width="80" height="48" rx="6" fill="{GREEN}" opacity="0.45"/>
  <rect x="{cx + cw * 0.58 + 128}" y="{cy + 124}" width="80" height="48" rx="6" fill="{HAIR}"/>
  {text(cx + cw * 0.58 + 24, cy + 308, "Open desktop", size=12, fill=CREAM, weight=600)}
  {text(cx + cw * 0.58 + 24, cy + 332, "Sleep", size=12, fill="#B0AAA0")}
  {text(cx + cw * 0.58 + 24, cy + 364, "Connecting only while starting.", size=11, fill="#B0AAA0")}
''',
        label="Bot conversation and Computer rail in a macOS window",
    )


def design_canvas() -> str:
    chrome, cx, cy, cw, ch = macos_window(70, 56, 820, 448, "Cortex Design · Untitled canvas")
    return wrap(
        chrome
        + f'''
  <rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" rx="8" fill="{RAIL}"/>
  <rect x="{cx + 24}" y="{cy + 24}" width="280" height="200" rx="8" fill="{CREAM}" stroke="{INK}" stroke-width="1.5"/>
  <rect x="{cx + 26}" y="{cy + 26}" width="276" height="196" rx="6" fill="none" stroke="{GREEN}" stroke-width="2"/>
  {text(cx + 40, cy + 56, "Frame 01", size=12, fill=MUTED, weight=600)}
  <rect x="{cx + 40}" y="{cy + 72}" width="160" height="28" rx="6" fill="{INK}"/>
  {text(cx + 120, cy + 91, "Primary", size=12, fill=CREAM, weight=600, anchor="middle")}
  <rect x="{cx + 40}" y="{cy + 112}" width="200" height="12" rx="2" fill="{LINE}"/>
  <rect x="{cx + 40}" y="{cy + 132}" width="168" height="12" rx="2" fill="{LINE}"/>
  <rect x="{cx + 328}" y="{cy + 48}" width="220" height="140" rx="8" fill="{CREAM}" stroke="{LINE}"/>
  {text(cx + 344, cy + 80, "Note", size=12, fill=MUTED, weight=600)}
  {text(cx + 344, cy + 108, "Hosted from Chat or Code.", size=13, fill=INK)}
  {text(cx + 344, cy + 132, "Not a markdown sidecar.", size=13, fill=INK)}
  <rect x="{cx + cw - 200}" y="{cy}" width="200" height="{ch}" fill="{CREAM}" stroke="{LINE}"/>
  {text(cx + cw - 184, cy + 36, "Library", size=13, fill=INK, weight=600)}
  {text(cx + cw - 184, cy + 68, "Components", size=12, fill=MUTED)}
  {text(cx + cw - 184, cy + 92, "Pages", size=12, fill=MUTED)}
  {text(cx + cw - 184, cy + 116, "Tokens", size=12, fill=MUTED)}
  {text(cx + 24, cy + ch - 24, "Working UI is the Design desktop app.", size=12, fill=MUTED)}
''',
        label="Design canvas with frames and library in a macOS window",
    )


def desktop() -> str:
    chrome, cx, cy, cw, ch = macos_window(100, 80, 760, 400, "Cortex Desktop")
    return wrap(
        chrome
        + f'''
  {text(cx + 12, cy + 28, "This PC  ·  SSH  ·  Design", size=13, fill=MUTED, weight=600)}
  <rect x="{cx}" y="{cy + 48}" width="230" height="240" rx="10" fill="{RAIL}" stroke="{LINE}"/>
  {text(cx + 20, cy + 84, "This PC", size=15, fill=INK, weight=600)}
  {text(cx + 20, cy + 112, "Paired host for Code", size=13, fill=MUTED)}
  {text(cx + 20, cy + 136, "and Bot. Not in the browser.", size=13, fill=MUTED)}
  <rect x="{cx + 250}" y="{cy + 48}" width="230" height="240" rx="10" fill="{RAIL}" stroke="{LINE}"/>
  {text(cx + 270, cy + 84, "SSH", size=15, fill=INK, weight=600)}
  {text(cx + 270, cy + 112, "A registered host.", size=13, fill=MUTED)}
  {text(cx + 270, cy + 136, "Shell only, no desktop.", size=13, fill=MUTED)}
  <rect x="{cx + 500}" y="{cy + 48}" width="236" height="240" rx="10" fill="{RAIL}" stroke="{GREEN}" stroke-width="2"/>
  {text(cx + 520, cy + 84, "Design", size=15, fill=GREEN, weight=600)}
  {text(cx + 520, cy + 112, "Working UI lives here.", size=13, fill=INK)}
  {text(cx + 520, cy + 136, "No /design web mode.", size=13, fill=MUTED)}
''',
        label="Cortex desktop surfaces in a macOS window",
    )


def cli_terminal() -> str:
    chrome, cx, cy, cw, ch = terminal_window(80, 56, 800, 448, "cortex — Cortex CLI — 120×40")
    return wrap(
        chrome
        + f'''
  {mono(cx + 8, cy + 28, "Welcome to Cortex, the coding agent CLI", size=14)}
  {mono(cx + 8, cy + 56, "v0.1  ·  / commands  ·  Enter to send", size=12, fill="#B0AAA0")}
  <path d="M{cx} {cy + ch - 92} H{cx + cw}" stroke="{HAIR}"/>
  <path d="M{cx} {cy + ch - 90} H{cx + cw}" stroke="#2A2824"/>
  {mono(cx + 8, cy + ch - 58, "> add a /healthz endpoint and cover it with a test", size=13)}
  <rect x="{cx + 8}" y="{cy + ch - 70}" width="8" height="16" fill="{GREEN}"/>
  <path d="M{cx} {cy + ch - 36} H{cx + cw}" stroke="{HAIR}"/>
  <path d="M{cx} {cy + ch - 34} H{cx + cw}" stroke="#2A2824"/>
  {mono(cx + 8, cy + ch - 12, "Cortex Mini 1", size=11, fill="#B0AAA0")}
  <text x="{cx + cw - 8}" y="{cy + ch - 12}" text-anchor="end" font-family="IBM Plex Mono, ui-monospace, monospace" font-size="11" fill="#B0AAA0">? help</text>
''',
        label="Cortex CLI terminal frame",
    )


def security() -> str:
    chrome, cx, cy, cw, ch = macos_window(80, 64, 800, 432, "Where code runs")
    boxes = []
    for i, (title, body) in enumerate(
        (
            ("Chat Python", "Small snippet sandbox.\nNo workspace."),
            ("Code Cloud", "Isolated guest.\nHeadless."),
            ("Bot computer", "Isolated guest.\nDesktop + shell."),
        )
    ):
        bx = cx + 16 + i * 250
        boxes.append(
            f'''
  <rect x="{bx}" y="{cy + 36}" width="232" height="220" rx="12" fill="{RAIL}" stroke="{LINE}"/>
  <rect x="{bx}" y="{cy + 36}" width="232" height="6" rx="3" fill="{GREEN}"/>
  {text(bx + 16, cy + 80, title, size=16, fill=INK, weight=600)}
  {text(bx + 16, cy + 116, body.splitlines()[0], size=13, fill=MUTED)}
  {text(bx + 16, cy + 140, body.splitlines()[1], size=13, fill=MUTED)}
'''
        )
    return wrap(
        chrome
        + "".join(boxes)
        + text(cx + 16, cy + 300, "Do not mix them. Chat Python cannot see a Code repository.", size=13, fill=INK),
        label="Three Cortex sandboxes in a macOS window",
    )


def approvals() -> str:
    chrome, cx, cy, cw, ch = macos_window(140, 90, 680, 380, "Bot · Confirm")
    return wrap(
        chrome
        + f'''
  {text(cx + 24, cy + 40, "Allow this computer step?", size=18, fill=INK, weight=600)}
  {text(cx + 24, cy + 72, "Confirming runs the parked action.", size=14, fill=MUTED)}
  <rect x="{cx + 24}" y="{cy + 110}" width="{cw - 48}" height="72" rx="10" fill="{RAIL}"/>
  {text(cx + 40, cy + 154, "grounded_click  ·  Submit form", size=14, fill=INK)}
  <rect x="{cx + 24}" y="{cy + 210}" width="140" height="40" rx="8" fill="{INK}"/>
  {text(cx + 94, cy + 236, "Allow", size=14, fill=CREAM, weight=600, anchor="middle")}
  <rect x="{cx + 176}" y="{cy + 210}" width="140" height="40" rx="8" fill="{CREAM}" stroke="{INK}"/>
  {text(cx + 246, cy + 236, "Deny", size=14, fill=INK, weight=600, anchor="middle")}
  <rect x="{cx + 328}" y="{cy + 210}" width="160" height="40" rx="8" fill="{SELECT}" stroke="{GREEN}" stroke-width="2"/>
  {text(cx + 408, cy + 236, "Always", size=14, fill=GREEN, weight=600, anchor="middle")}
''',
        label="Bot approval Allow Deny Always in a macOS window",
    )


def github() -> str:
    chrome, cx, cy, cw, ch = macos_window(100, 80, 760, 400, "Code · Connect GitHub")
    return wrap(
        chrome
        + f'''
  {text(cx + 20, cy + 40, "Connect GitHub", size=20, fill=INK, weight=600)}
  {text(cx + 20, cy + 76, "Code Home  ·  repository picker  ·  Settings → Integrations", size=13, fill=MUTED)}
  <rect x="{cx + 20}" y="{cy + 110}" width="280" height="48" rx="10" fill="{INK}"/>
  {text(cx + 160, cy + 140, "Connect GitHub", size=14, fill=CREAM, weight=600, anchor="middle")}
  <rect x="{cx + 320}" y="{cy + 110}" width="200" height="48" rx="10" fill="{RAIL}" stroke="{LINE}"/>
  {text(cx + 420, cy + 140, "Reconnect", size=14, fill=INK, weight=600, anchor="middle")}
  {text(cx + 20, cy + 200, "There is no personal-access-token field.", size=14, fill=INK)}
  {text(cx + 20, cy + 228, "If GitHub is unavailable on this deployment,", size=14, fill=MUTED)}
  {text(cx + 20, cy + 256, "the product draws no Connect control.", size=14, fill=MUTED)}
''',
        label="Connect GitHub control in a macOS window",
    )


FRAMES = {
    "switcher.svg": switcher,
    "chat-composer.svg": chat_composer,
    "chat-projects.svg": chat_projects,
    "chat-research.svg": chat_research,
    "chat-images.svg": chat_images,
    "code-session.svg": code_session,
    "code-cloud.svg": code_cloud,
    "bot-computer.svg": bot_computer,
    "design-canvas.svg": design_canvas,
    "desktop.svg": desktop,
    "cli-terminal.svg": cli_terminal,
    "security.svg": security,
    "approvals.svg": approvals,
    "github.svg": github,
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in FRAMES.items():
        path = OUT / name
        path.write_text(fn(), encoding="utf-8")
        print(f"wrote {path.relative_to(OUT.parent.parent)}")


if __name__ == "__main__":
    main()
