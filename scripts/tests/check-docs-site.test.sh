#!/usr/bin/env bash
# Holds scripts/check-docs-site.mjs. No Mintlify CLI: a throwaway tree with a
# fake ErrorCode, a fake router, and a couple of MDX files is enough to prove
# a matching site passes and that a wrong domain, a missing page, a dead
# navigation entry, an image, a leaked auth internal, or an invented /v1 path
# fails.
set -euo pipefail

root="$(cd "$(dirname "$0")/../.." && pwd)"
script="$root/scripts/check-docs-site.mjs"

fail() { echo "check-docs-site.test.sh: $*" >&2; exit 1; }

tmp="$(mktemp -d)"
cleanup() { rm -rf "$tmp"; }
trap cleanup EXIT

seed() {
  local dest="$1"
  mkdir -p \
    "$dest/crates/cortex-core/src" \
    "$dest/crates/cortex-api/src" \
    "$dest/packages/api-types/src" \
    "$dest/site/problems" \
    "$dest/site/logo"
  cat > "$dest/crates/cortex-core/src/error.rs" <<'RS'
pub const PROBLEM_TYPE_BASE: &str = "https://docs.cortex.foundation/problems";

impl ErrorCode {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::NotFound => "not_found",
            Self::Internal => "internal",
        }
    }
}
RS
  cat > "$dest/packages/api-types/src/errors.ts" <<'TS'
export const PROBLEM_TYPE_BASE = 'https://docs.cortex.foundation/problems' as const;
TS
  cat > "$dest/crates/cortex-api/src/router.rs" <<'RS'
        .route("/healthz", get(health::liveness))
        .route("/conversations", get(list))
        .route("/conversations/{id}", get(get).patch(patch))
RS
  printf '<svg xmlns="http://www.w3.org/2000/svg"></svg>' > "$dest/site/favicon.svg"
  printf '<svg xmlns="http://www.w3.org/2000/svg"></svg>' > "$dest/site/logo/light.svg"
  printf '<svg xmlns="http://www.w3.org/2000/svg"></svg>' > "$dest/site/logo/dark.svg"
  write_docs_json "$dest" '"pages": ["problems/not_found", "problems/internal"]'
  for code in not_found internal; do
    cat > "$dest/site/problems/${code}.mdx" <<MDX
---
title: "${code}"
description: "A problem page."
---

\`type\` is \`https://docs.cortex.foundation/problems/${code}\`.

| Method | Path |
| --- | --- |
| \`GET\` | \`/v1/conversations\` |
MDX
  done
}

# A minimal docs.json with the product tabs the checker requires. The first
# argument is the tree; the second is the JSON for the "Errors" group body.
write_docs_json() {
  local dest="$1"
  local errors_group_body="$2"
  local tab_groups=""
  for tab in Chat Code Bot CLI Design Security; do
    tab_groups="$tab_groups{ \"tab\": \"$tab\", \"icon\": \"star\", \"groups\": [ { \"group\": \"Overview\", \"icon\": \"star\", \"pages\": [\"problems/not_found\"] } ] },"
  done
  cat > "$dest/site/docs.json" <<JSON
{
  "theme": "mint",
  "name": "Cortex",
  "favicon": "/favicon.svg",
  "logo": { "light": "/logo/light.svg", "dark": "/logo/dark.svg", "href": "https://docs.cortex.foundation" },
  "navbar": {
    "links": [ { "label": "Website", "href": "https://cortex.foundation" } ],
    "primary": { "type": "button", "label": "Open Cortex", "href": "https://cortex.foundation" }
  },
  "navigation": {
    "tabs": [
      $tab_groups
      {
        "tab": "Reference",
        "icon": "book",
        "groups": [
          {
            "group": "Errors",
            "icon": "triangle-exclamation",
            $errors_group_body
          }
        ]
      }
    ]
  }
}
JSON
}

must_fail() {
  local dir="$1"
  local needle="$2"
  local out
  if out="$(CORTEX_CHECK_ROOT="$dir/site" node "$script" "$dir" 2>&1)"; then
    fail "expected failure mentioning ${needle}, got success: ${out}"
  fi
  printf '%s' "$out" | grep -q -- "$needle" || fail "expected stderr to mention ${needle}, got: ${out}"
}

# Happy path: matching domain, both codes, documented route exists.
happy="$tmp/happy"
seed "$happy"
out="$(CORTEX_CHECK_ROOT="$happy/site" node "$script" "$happy" 2>&1)" || fail "happy tree should pass, got: $out"

# The site is independent of the backend checkout and the caller's directory.
out="$(cd "$tmp" && CORTEX_CHECK_ROOT="$happy/site" node "$script" 2>&1)" ||
  fail "standalone site should pass, got: $out"
[[ "$out" == *"backend contract not checked"* ]] || fail "standalone check must disclose its scope"
if CORTEX_CHECK_ROOT="$happy/site" node "$script" "$tmp/absent-backend" >/dev/null 2>&1; then
  fail "an explicitly requested missing backend must fail"
fi

# Wrong domain on the Rust constant.
wrong="$tmp/wrong-base"
seed "$wrong"
sed -i 's|https://docs.cortex.foundation/problems|https://docs.cortex.sh/problems|' \
  "$wrong/crates/cortex-core/src/error.rs"
must_fail "$wrong" "docs.cortex.foundation"

# Missing problem page.
missing="$tmp/missing-page"
seed "$missing"
rm -f "$missing/site/problems/internal.mdx"
must_fail "$missing" "internal"

# Invented /v1 path.
invented="$tmp/invented"
seed "$invented"
printf '\n`GET` `/v1/not-a-real-route`\n' >> "$invented/site/problems/not_found.mdx"
must_fail "$invented" "not-a-real-route"

# Stale host in the docs tree.
stale="$tmp/stale-host"
seed "$stale"
printf '\nSee https://docs.cortex.sh/problems/not_found\n' >> "$stale/site/problems/not_found.mdx"
must_fail "$stale" "docs.cortex.sh"

# Navigation must be tabs, one per application.
groupsnav="$tmp/groups-nav"
seed "$groupsnav"
cat > "$groupsnav/site/docs.json" <<'JSON'
{
  "theme": "mint",
  "name": "Cortex",
  "favicon": "/favicon.svg",
  "logo": { "light": "/logo/light.svg", "dark": "/logo/dark.svg", "href": "https://docs.cortex.foundation" },
  "navigation": {
    "groups": [ { "group": "Problems", "icon": "list", "pages": ["problems/not_found", "problems/internal"] } ]
  }
}
JSON
must_fail "$groupsnav" "navigation.tabs"

# A product tab may not go missing.
notab="$tmp/no-bot-tab"
seed "$notab"
sed -i 's/"tab": "Bot"/"tab": "Agents"/' "$notab/site/docs.json"
must_fail "$notab" '"Bot" tab'

# Every tab and group carries an icon.
noicon="$tmp/no-icon"
seed "$noicon"
sed -i '0,/"icon": "star",/s//"icon": "",/' "$noicon/site/docs.json"
must_fail "$noicon" "has no icon"

# The theme is the Mintlify starter theme.
theme="$tmp/theme"
seed "$theme"
sed -i 's/"theme": "mint"/"theme": "willow"/' "$theme/site/docs.json"
must_fail "$theme" 'theme must be "mint"'

# Auth / OAuth internals must not ship on the public docs site.
authpage="$tmp/auth-page"
seed "$authpage"
mkdir -p "$authpage/site/api"
cat > "$authpage/site/api/authentication.mdx" <<'MDX'
---
title: "Authentication"
description: "Sign in."
icon: "lock"
---
Sign in.
MDX
must_fail "$authpage" "authentication.mdx"

authpath="$tmp/auth-path"
seed "$authpath"
printf '\nSee `/v1/auth/refresh`.\n' >> "$authpath/site/problems/not_found.mdx"
must_fail "$authpath" "/auth/"

oauthpath="$tmp/oauth-path"
seed "$oauthpath"
printf '\nSee `/v1/code/github/oauth/start`.\n' >> "$oauthpath/site/problems/not_found.mdx"
must_fail "$oauthpath" "/oauth/"

refresh="$tmp/refresh-token"
seed "$refresh"
printf '\nBody field `refresh_token`.\n' >> "$refresh/site/problems/not_found.mdx"
must_fail "$refresh" "refresh_token"

workos="$tmp/workos"
seed "$workos"
printf '\nWorkOS AuthKit.\n' >> "$workos/site/problems/not_found.mdx"
must_fail "$workos" "WorkOS"

cookie="$tmp/cortex-rt"
seed "$cookie"
printf '\nhttpOnly `cortex_rt` cookie.\n' >> "$cookie/site/problems/not_found.mdx"
must_fail "$cookie" "cortex_rt"

authnav="$tmp/auth-nav"
seed "$authnav"
write_docs_json "$authnav" '"pages": ["problems/not_found", "problems/internal", "api/authentication", "api/oauth"]'
must_fail "$authnav" "api/authentication"

# Images are not allowed: the site uses icons.
img="$tmp/img"
seed "$img"
printf '\n<img src="/logo/light.svg" alt="logo" />\n' >> "$img/site/problems/not_found.mdx"
must_fail "$img" "no images"

frame="$tmp/frame"
seed "$frame"
printf '\n<Frame><p>x</p></Frame>\n' >> "$frame/site/problems/not_found.mdx"
must_fail "$frame" "no images"

mdimg="$tmp/md-img"
seed "$mdimg"
printf '\n![alt](/logo/light.svg)\n' >> "$mdimg/site/problems/not_found.mdx"
must_fail "$mdimg" "no images"

imgfm="$tmp/img-frontmatter"
seed "$imgfm"
sed -i 's|^description: "A problem page."|description: "A problem page."\nimage: "/logo/light.svg"|' "$imgfm/site/problems/not_found.mdx"
must_fail "$imgfm" "no images"

# Frontmatter: description length and unique titles.
longdesc="$tmp/long-desc"
seed "$longdesc"
long="$(printf 'x%.0s' $(seq 1 170))"
sed -i "s|^description: \"A problem page.\"|description: \"$long\"|" "$longdesc/site/problems/not_found.mdx"
must_fail "$longdesc" "max 160"

duptitle="$tmp/dup-title"
seed "$duptitle"
sed -i 's|^title: "internal"|title: "not_found"|' "$duptitle/site/problems/internal.mdx"
must_fail "$duptitle" "repeats the title"

# A navigation slug with no MDX page must fail (Mintlify would ship a 404 link).
# Nested `{ group, pages }` is included so a one-level walker cannot sneak through.
missingnav="$tmp/missing-nav"
seed "$missingnav"
write_docs_json "$missingnav" '"pages": ["problems/not_found", "missing-mintlify-page", { "group": "Nested", "icon": "list", "pages": ["also-missing-mintlify-page"] }]'
must_fail "$missingnav" "missing-mintlify-page"
must_fail "$missingnav" "also-missing-mintlify-page"

# A group `root` is a page the sidebar title opens, and it is not repeated in
# `pages`. Walking only `pages` would publish a dead group title.
missingroot="$tmp/missing-root"
seed "$missingroot"
write_docs_json "$missingroot" '"root": "missing-root-page", "pages": ["problems/not_found", "problems/internal"]'
must_fail "$missingroot" "missing-root-page"

# The same group with a root that does exist must pass.
goodroot="$tmp/good-root"
seed "$goodroot"
write_docs_json "$goodroot" '"root": "problems/not_found", "pages": ["problems/internal"]'
out="$(CORTEX_CHECK_ROOT="$goodroot/site" node "$script" "$goodroot" 2>&1)" ||
  fail "a group root backed by an MDX page should pass, got: $out"

# An internal link inside a page must resolve to an MDX page.
deadlink="$tmp/dead-link"
seed "$deadlink"
printf '\nSee [the missing page](/reference/does-not-exist).\n' >> "$deadlink/site/problems/not_found.mdx"
must_fail "$deadlink" "reference/does-not-exist"

# A navbar href with no MDX page must fail even when every `pages` slug exists.
missinghref="$tmp/missing-href"
seed "$missinghref"
sed -i 's|"href": "https://cortex.foundation" }$|"href": "/missing-mintlify-page" }|' "$missinghref/site/docs.json"
sed -i '0,/"label": "Website", "href": "https:\/\/cortex.foundation"/s//"label": "Website", "href": "\/missing-mintlify-page"/' "$missinghref/site/docs.json"
must_fail "$missinghref" "missing-mintlify-page"

echo "check-docs-site: ok"
