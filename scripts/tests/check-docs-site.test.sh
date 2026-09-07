#!/usr/bin/env bash
# Holds scripts/check-docs-site.mjs. No Mintlify CLI: a throwaway tree with a
# fake ErrorCode, a fake router, and a couple of MDX files is enough to prove
# a matching site passes and that a wrong domain, a missing page, a dead
# navigation entry, or an invented /v1 path fails.
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
    "$dest/site/problems"
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
  cat > "$dest/site/docs.json" <<'JSON'
{
  "name": "Cortex",
  "logo": { "href": "https://docs.cortex.foundation" },
  "navbar": {
    "links": [
      { "label": "Home", "href": "/" },
      { "label": "Documentation", "href": "/problems/not_found" }
    ]
  },
  "navigation": {
    "tabs": [
      {
        "tab": "API",
        "groups": [
          {
            "group": "Problems",
            "pages": ["problems/not_found", "problems/internal"]
          }
        ]
      }
    ]
  }
}
JSON
  for code in not_found internal; do
    cat > "$dest/site/problems/${code}.mdx" <<MDX
---
title: "${code}"
---

\`type\` is \`https://docs.cortex.foundation/problems/${code}\`.

| Method | Path |
| --- | --- |
| \`GET\` | \`/v1/conversations\` |
MDX
  done
}

must_fail() {
  local dir="$1"
  local needle="$2"
  local out
  if out="$(CORTEX_CHECK_ROOT="$dir/site" node "$script" "$dir" 2>&1)"; then
    fail "expected failure mentioning ${needle}, got success: ${out}"
  fi
  printf '%s' "$out" | grep -q "$needle" || fail "expected stderr to mention ${needle}, got: ${out}"
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

# Product chrome in the top navbar (Chat | Code | Bot belongs in documentation tabs).
chrome="$tmp/chrome-nav"
seed "$chrome"
cat > "$chrome/site/docs.json" <<'JSON'
{
  "name": "Cortex",
  "logo": { "href": "https://docs.cortex.foundation" },
  "navbar": {
    "links": [
      { "label": "Home", "href": "/" },
      { "label": "Chat", "href": "/chat" },
      { "label": "Code", "href": "/code" },
      { "label": "Bot", "href": "/bot" }
    ]
  }
}
JSON
must_fail "$chrome" "product chrome"

# Brand-green Install CTA on the navbar.
primary="$tmp/primary-cta"
seed "$primary"
cat > "$primary/site/docs.json" <<'JSON'
{
  "name": "Cortex",
  "logo": { "href": "https://docs.cortex.foundation" },
  "navbar": {
    "links": [
      { "label": "Home", "href": "/" },
      { "label": "Documentation", "href": "/problems/not_found" }
    ],
    "primary": { "type": "button", "label": "Install", "href": "/problems/not_found" }
  }
}
JSON
must_fail "$primary" "navbar.primary"

# Auth / OAuth internals must not ship on the public docs site.
authpage="$tmp/auth-page"
seed "$authpage"
mkdir -p "$authpage/site/api"
cat > "$authpage/site/api/authentication.mdx" <<'MDX'
---
title: "Authentication"
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
cat > "$authnav/site/docs.json" <<'JSON'
{
  "name": "Cortex",
  "logo": { "href": "https://docs.cortex.foundation" },
  "navbar": {
    "links": [
      { "label": "Home", "href": "/" },
      { "label": "Documentation", "href": "/problems/not_found" }
    ]
  },
  "navigation": {
    "tabs": [
      {
        "tab": "API",
        "groups": [
          { "group": "App API", "pages": ["api/overview", "api/authentication", "api/oauth"] }
        ]
      }
    ]
  }
}
JSON
must_fail "$authnav" "api/authentication"

# A navigation slug with no MDX page must fail (Mintlify would ship a 404 link).
# Nested `{ group, pages }` is included so a one-level walker cannot sneak through.
missingnav="$tmp/missing-nav"
seed "$missingnav"
cat > "$missingnav/site/docs.json" <<'JSON'
{
  "name": "Cortex",
  "logo": { "href": "https://docs.cortex.foundation" },
  "navbar": {
    "links": [
      { "label": "Home", "href": "/" },
      { "label": "Documentation", "href": "/problems/not_found" }
    ]
  },
  "navigation": {
    "tabs": [
      {
        "tab": "API",
        "groups": [
          {
            "group": "Public",
            "pages": [
              "problems/not_found",
              "missing-mintlify-page",
              { "group": "Nested", "pages": ["also-missing-mintlify-page"] }
            ]
          }
        ]
      }
    ]
  }
}
JSON
must_fail "$missingnav" "missing-mintlify-page"
must_fail "$missingnav" "also-missing-mintlify-page"

# A navbar href with no MDX page must fail even when every `pages` slug exists.
missinghref="$tmp/missing-href"
seed "$missinghref"
cat > "$missinghref/site/docs.json" <<'JSON'
{
  "name": "Cortex",
  "logo": { "href": "https://docs.cortex.foundation" },
  "navbar": {
    "links": [
      { "label": "Home", "href": "/" },
      { "label": "Documentation", "href": "/missing-mintlify-page" }
    ]
  },
  "navigation": {
    "tabs": [
      {
        "tab": "API",
        "groups": [
          { "group": "Problems", "pages": ["problems/not_found", "problems/internal"] }
        ]
      }
    ]
  }
}
JSON
must_fail "$missinghref" "missing-mintlify-page"

echo "check-docs-site: ok"
