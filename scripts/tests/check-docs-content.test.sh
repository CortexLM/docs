#!/usr/bin/env bash
# Holds scripts/check-docs-content.mjs. A throwaway site with one hub, one page and two
# problem pages is enough to prove that a clean tree passes and that every rule the
# script claims to enforce actually fires: frontmatter, the description ceiling,
# duplicate titles, forbidden vocabulary, emoji, API paths off the API pages, dead
# links, unallowed external links, the closing section, page length, unbalanced
# components, iconless cards, unsafe screenshots and a hub with no card grid.
#
# It also pins the two deliberate exemptions, which are the ones a future edit is most
# likely to break by accident: the card-suit block is not emoji, and problem pages are
# exempt from the icon, closing-section and length rules.
set -euo pipefail

root="$(cd "$(dirname "$0")/../.." && pwd)"
script="$root/scripts/check-docs-content.mjs"

fail() { echo "check-docs-content.test.sh: $*" >&2; exit 1; }

tmp="$(mktemp -d)"
cleanup() { rm -rf "$tmp"; }
trap cleanup EXIT

# The word-count rule wants 250; this is 450.
filler() {
  local i
  for i in $(seq 1 30); do
    printf 'The documentation describes what the product does and how a reader uses it. '
  done
  printf '\n'
}

seed() {
  local dest="$1"
  mkdir -p "$dest/site/guide" "$dest/site/problems"

  cat > "$dest/site/index.mdx" <<'MDX'
---
title: "Cortex Docs"
description: "Everything Cortex does, one section per application."
icon: "house"
---

Pick an application.

<CardGroup cols={2}>
  <Card title="Guide" icon="book" href="/guide/thing">
    How the thing works.
  </Card>
</CardGroup>

MDX
  filler >> "$dest/site/index.mdx"
  printf '\n## Related\n\n- [Thing](/guide/thing)\n' >> "$dest/site/index.mdx"

  cat > "$dest/site/guide/thing.mdx" <<'MDX'
---
title: "The thing"
description: "What the thing is and how to use it."
icon: "wrench"
---

<Steps>
  <Step title="Open it">
    Open the thing.
  </Step>
</Steps>

MDX
  filler >> "$dest/site/guide/thing.mdx"
  printf '\n## Related\n\n- [Home](/)\n' >> "$dest/site/guide/thing.mdx"

  # The error index is a table of codes, not a card grid, so it is not a hub.
  cat > "$dest/site/problems/index.mdx" <<'MDX'
---
title: "Problem types"
description: "Every error code this API can return."
icon: "triangle-exclamation"
---

| Code | Meaning |
| --- | --- |
| `not_found` | Nothing at that address. |

MDX
  filler >> "$dest/site/problems/index.mdx"
  printf '\n## Related\n\n- [Home](/)\n' >> "$dest/site/problems/index.mdx"

  # A problem page: no icon, no closing section, far under 250 words, and an API path.
  cat > "$dest/site/problems/not_found.mdx" <<'MDX'
---
title: "not_found"
description: "Nothing exists at that address."
---

Returned by `GET /v1/conversations/{id}` when the conversation is gone.
MDX

  cat > "$dest/site/docs.json" <<'JSON'
{
  "theme": "mint",
  "name": "Cortex",
  "navigation": {
    "tabs": [
      {
        "tab": "Get started",
        "icon": "rocket",
        "groups": [
          { "group": "Welcome", "icon": "hand-wave", "pages": ["index", "guide/thing"] }
        ]
      },
      {
        "tab": "Reference",
        "icon": "book-open",
        "groups": [
          {
            "group": "Errors",
            "icon": "triangle-exclamation",
            "root": "problems/index",
            "pages": ["problems/not_found"]
          }
        ]
      }
    ]
  }
}
JSON
}

run() { CORTEX_CHECK_ROOT="$1/site" node "$script" "${@:2}" 2>&1; }

must_fail() {
  local dir="$1" needle="$2" out
  if out="$(run "$dir")"; then
    fail "expected failure mentioning ${needle}, got success: ${out}"
  fi
  printf '%s' "$out" | grep -q -- "$needle" || fail "expected output to mention ${needle}, got: ${out}"
}

# A throwaway copy of the happy tree, so each case starts from a clean site.
fresh() {
  local dir="$tmp/$1"
  cp -r "$tmp/happy" "$dir"
  printf '%s' "$dir"
}

# --- happy path ------------------------------------------------------------------
happy="$tmp/happy"
seed "$happy"
out="$(run "$happy")" || fail "happy tree should pass, got: $out"
[[ "$out" == *"4 page(s)"* ]] || fail "expected all four pages to be checked, got: $out"

# Page count comes from docs.json navigation, group roots included. A page the
# navigation does not reach is not checked, and check-docs-site.mjs is what catches it.
out="$(run "$happy" guide/thing)" || fail "single-page run should pass, got: $out"
[[ "$out" == *"1 page(s)"* ]] || fail "expected a one-page run, got: $out"

# The site is independent of the caller's directory.
out="$(cd "$tmp" && CORTEX_CHECK_ROOT="$happy/site" node "$script" 2>&1)" ||
  fail "standalone run should pass, got: $out"

# CRLF is what the real tree uses; frontmatter must still parse.
crlf="$(fresh crlf)"
sed -i 's/$/\r/' "$crlf/site/guide/thing.mdx"
out="$(run "$crlf")" || fail "CRLF page should pass, got: $out"

# --- frontmatter -----------------------------------------------------------------
d="$(fresh no-title)"
sed -i '/^title: /d' "$d/site/guide/thing.mdx"
must_fail "$d" "missing title"

d="$(fresh no-description)"
sed -i '/^description: /d' "$d/site/guide/thing.mdx"
must_fail "$d" "missing description"

d="$(fresh no-icon)"
sed -i '/^icon: /d' "$d/site/guide/thing.mdx"
must_fail "$d" "missing icon"

d="$(fresh long-description)"
long="$(printf 'x%.0s' $(seq 1 161))"
sed -i "s|^description: .*|description: \"$long\"|" "$d/site/guide/thing.mdx"
must_fail "$d" "161 chars"

d="$(fresh duplicate-title)"
sed -i 's|^title: "The thing"|title: "Cortex Docs"|' "$d/site/guide/thing.mdx"
must_fail "$d" "duplicates"

# --- forbidden vocabulary --------------------------------------------------------
d="$(fresh vendor)"
printf '\nCortex is not Anthropic.\n' >> "$d/site/guide/thing.mdx"
must_fail "$d" "competitor: Anthropic"

d="$(fresh auth-internal)"
printf '\nThe `refresh_token` is rotated.\n' >> "$d/site/guide/thing.mdx"
must_fail "$d" "refresh_token"

d="$(fresh emoji)"
printf '\nShip it '"$(printf '\xf0\x9f\x9a\x80')"'\n' >> "$d/site/guide/thing.mdx"
must_fail "$d" "emoji"

# The card suits are excluded from the emoji range on purpose: the terminal interface
# prints them as row markers, so they are product glyphs inside a quoted string.
d="$(fresh card-suit)"
printf '\nThe status line reads `'"$(printf '\xe2\x99\xa6')"' Thought for 4s`.\n' \
  >> "$d/site/guide/thing.mdx"
out="$(run "$d")" || fail "a card suit is not emoji, got: $out"

# --- local product screenshots ---------------------------------------------------
d="$(fresh images)"
mkdir -p "$d/site/images/product"
for file in shot-light.webp shot-dark.webp shot.png shot.jpg; do
  printf 'screenshot fixture' > "$d/site/images/product/$file"
done
cat >> "$d/site/guide/thing.mdx" <<'MDX'

<Frame caption="Interface preview">
  <img src="/images/product/shot-light.webp" alt="Cortex home" width="3360" height="2240" loading="lazy" className="block dark:hidden" />
  <img src="/images/product/shot-dark.webp" alt="Cortex home in dark mode" width="3360" height="2240" className="hidden dark:block" />
</Frame>
<img
  alt='Changes > proposed files'
  src='/images/product/shot.png'
/>
<img src="/images/product/shot.jpg" alt="The library" />

`<img src="https://cortex.foundation/example.png" />`
```mdx
<img src="https://cortex.foundation/example.png" />
```
MDX
out="$(run "$d")" || fail "accessible local screenshots should pass, got: $out"

image_failure() {
  local dir markup="$2" needle="$3"
  dir="$(fresh "image-$1")"
  mkdir -p "$dir/site/images/product"
  printf 'screenshot fixture' > "$dir/site/images/product/shot.webp"
  printf '\n%s\n' "$markup" >> "$dir/site/guide/thing.mdx"
  must_fail "$dir" "$needle"
}

image_failure no-alt '<img src="/images/product/shot.webp" />' 'alt text must be nonempty'
image_failure empty-alt '<img src="/images/product/shot.webp" alt="&#32;&nbsp;" />' 'alt text must be nonempty'
image_failure missing '<img src="/images/product/absent.webp" alt="Cortex home" />' 'missing or unreadable'
image_failure remote '<img src="https://cortex.foundation/track.png" alt="Cortex home" />' 'safe local'
image_failure protocol-relative '<img src="//cortex.foundation/track.png" alt="Cortex home" />' 'safe local'
image_failure data '<img src="data:image/png;base64,AAAA" alt="Cortex home" />' 'safe local'
image_failure traversal '<img src="/images/product/../shot.webp" alt="Cortex home" />' 'safe local'
image_failure encoded '<img src="/images/product/%2e%2e/shot.webp" alt="Cortex home" />' 'safe local'
image_failure svg '<img src="/images/product/shot.svg" alt="Cortex home" />' 'safe local'
image_failure srcset '<img src="/images/product/shot.webp" alt="Cortex home" srcSet="//cortex.foundation/track.png 2x" />' 'unsupported image attribute'
image_failure expression '<img src="/images/product/shot.webp" alt={description} />' 'literal quoted'
image_failure spread '<img src="/images/product/shot.webp" alt="Cortex home" {...props} />' 'literal quoted'
image_failure media '<video src="https://cortex.foundation/track.mp4" />' 'unsupported media'
image_failure markdown '![Cortex home](/images/product/shot.webp)' 'markdown images are unsupported'
image_failure markdown-reference '![Cortex home][shot]' 'markdown images are unsupported'

d="$(fresh image-frontmatter)"
sed -i 's|^description: "What the thing is and how to use it."|description: "What the thing is and how to use it."\nimage: "/images/product/shot.webp"|' "$d/site/guide/thing.mdx"
must_fail "$d" "image frontmatter is unsupported"

d="$(fresh unbalanced-frame)"
printf '\n<Frame caption="Interface preview">\n' >> "$d/site/guide/thing.mdx"
must_fail "$d" "unbalanced <Frame>"

# --- API paths -------------------------------------------------------------------
# Allowed on the problem pages, as the happy path already proved. Not elsewhere.
d="$(fresh api-path)"
printf '\nCall /v1/conversations to list them.\n' >> "$d/site/guide/thing.mdx"
must_fail "$d" "non-API page"

# A fenced block is not prose, so it is not searched for API paths. The external-link
# rule does still read fences, so the host here has to be an allowed one.
d="$(fresh api-path-fenced)"
printf '\n```bash\ncurl https://api.cortex.foundation/v1/conversations\n```\n' >> "$d/site/guide/thing.mdx"
out="$(run "$d")" || fail "a fenced API path should be allowed, got: $out"

# --- links -----------------------------------------------------------------------
d="$(fresh dead-link)"
printf '\nSee [nothing](/guide/absent).\n' >> "$d/site/guide/thing.mdx"
must_fail "$d" "has no page"

# A link to a directory resolves through its index page.
d="$(fresh index-link)"
printf '\nSee [the errors](/problems).\n' >> "$d/site/guide/thing.mdx"
out="$(run "$d")" || fail "/problems should resolve to problems/index, got: $out"

d="$(fresh external-link)"
printf '\nSee [elsewhere](https://example.com/thing).\n' >> "$d/site/guide/thing.mdx"
must_fail "$d" "allowlist"

d="$(fresh allowed-external)"
printf '\nSee [the repo](https://github.com/CortexLM/backend).\n' >> "$d/site/guide/thing.mdx"
out="$(run "$d")" || fail "a CortexLM repo link should pass, got: $out"

# --- body --------------------------------------------------------------------------
d="$(fresh no-related)"
sed -i '/^## Related$/d' "$d/site/guide/thing.mdx"
must_fail "$d" "Related"

d="$(fresh thin)"
sed -i '/^The documentation describes/d' "$d/site/guide/thing.mdx"
must_fail "$d" "thin page"

d="$(fresh unbalanced)"
sed -i 's|^</Steps>$||' "$d/site/guide/thing.mdx"
must_fail "$d" "unbalanced <Steps>"

d="$(fresh card-no-icon)"
sed -i 's| icon="book"||' "$d/site/index.mdx"
must_fail "$d" "without icon"

d="$(fresh hub-no-cardgroup)"
sed -i 's|<CardGroup cols={2}>|<div>|; s|</CardGroup>|</div>|' "$d/site/index.mdx"
must_fail "$d" "hub page without a <CardGroup>"

echo "check-docs-content.test.sh: ok"
