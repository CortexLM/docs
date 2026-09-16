#!/usr/bin/env node
/**
 * Checks the public Mintlify site. Pass a backend checkout as the first
 * argument to also check the API contract and registered routes.
 *
 * # Why this exists
 *
 * `PROBLEM_TYPE_BASE` is wire contract: every error the API returns carries a
 * `type` URL under `https://docs.cortex.foundation/problems`, so each
 * `ErrorCode` needs a page there, and no page may document a code the API does
 * not emit. Documenting a `/v1/…` path the router does not register is the
 * same class of silent decay.
 *
 * The site is end-user documentation. Public MDX must not document sign-in
 * wire protocols (`/auth/`, `/oauth/`, refresh tokens, identity vendors, or the
 * session cookie), and it carries no images: every page and card uses an
 * icon. Navigation is `navigation.tabs`, one tab per application, so a reader
 * picks the product from the navbar the way they would on any large docs site.
 * Every navigation entry, group root, navbar link, and internal href must
 * resolve to an MDX page — Mintlify would otherwise publish a link that 404s
 * while the rest of this job stayed green.
 */

import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(process.env.CORTEX_CHECK_ROOT ?? fileURLToPath(new URL('..', import.meta.url)));
const BACKEND = process.argv[2] === undefined ? null : resolve(process.argv[2]);
const EXPECTED_BASE = 'https://docs.cortex.foundation/problems';
const OPERATIONAL = new Set(['/healthz', '/readyz', '/startupz']);
const PRODUCT_TABS = ['Chat', 'Code', 'Bot', 'CLI', 'Design', 'Security'];

const failures = [];

function fail(message) {
  failures.push(message);
}

function read(rel, root = ROOT) {
  const path = join(root, rel);
  if (!existsSync(path)) {
    fail(`missing ${rel}`);
    return '';
  }
  return readFileSync(path, 'utf8');
}

function walk(dir) {
  if (!existsSync(dir)) return [];
  const out = [];
  for (const ent of readdirSync(dir, { withFileTypes: true })) {
    if (['node_modules', '.mintlify', '.git', 'scripts'].includes(ent.name)) continue;
    const path = join(dir, ent.name);
    if (ent.isDirectory()) out.push(...walk(path));
    else out.push(path);
  }
  return out;
}

function rustErrorCodes(source) {
  const block = /pub const fn as_str\(self\)[\s\S]*?match self \{([\s\S]*?)\n        \}/.exec(
    source,
  );
  if (block === null) {
    fail('could not find `ErrorCode::as_str` in crates/cortex-core/src/error.rs');
    return [];
  }
  return [...block[1].matchAll(/=> "([a-z_]+)"/g)].map((m) => m[1]);
}

function rustProblemBase(source) {
  return /pub const PROBLEM_TYPE_BASE: &str = "([^"]+)";/.exec(source)?.[1] ?? null;
}

function tsProblemBase(source) {
  return /export const PROBLEM_TYPE_BASE = '([^']+)'/.exec(source)?.[1] ?? null;
}

const FORBIDDEN_AUTH_PAGES = ['api/authentication', 'api/oauth'];

function pushNavSlug(raw, out) {
  if (typeof raw !== 'string') return;
  const trimmed = raw.trim();
  if (
    trimmed === '' ||
    trimmed === '/' ||
    trimmed.startsWith('http://') ||
    trimmed.startsWith('https://') ||
    trimmed.startsWith('mailto:') ||
    trimmed.startsWith('#')
  ) {
    return;
  }
  const slug = trimmed.replace(/^\//, '').replace(/\.mdx?$/i, '');
  if (slug) out.push(slug);
}

/**
 * Mintlify `pages` entries are either a slug string or a nested `{ group, pages }`
 * object. `href` on navbar links, anchors and nav objects is the same contract:
 * an internal path must resolve to MDX.
 */
function collectNavPages(node, out = []) {
  if (node == null) return out;
  if (typeof node === 'string') {
    pushNavSlug(node, out);
    return out;
  }
  if (Array.isArray(node)) {
    for (const item of node) collectNavPages(item, out);
    return out;
  }
  if (typeof node !== 'object') return out;
  if (typeof node.page === 'string') pushNavSlug(node.page, out);
  if (typeof node.href === 'string') pushNavSlug(node.href, out);
  // A group's `root` is the page its title opens. It is not repeated in
  // `pages`, so walking only `pages` would leave a dead root link green.
  if (typeof node.root === 'string') pushNavSlug(node.root, out);
  if (Array.isArray(node.pages)) collectNavPages(node.pages, out);
  if (Array.isArray(node.groups)) collectNavPages(node.groups, out);
  if (Array.isArray(node.tabs)) collectNavPages(node.tabs, out);
  if (Array.isArray(node.anchors)) collectNavPages(node.anchors, out);
  if (Array.isArray(node.dropdowns)) collectNavPages(node.dropdowns, out);
  if (node.global) collectNavPages(node.global, out);
  return out;
}

function navPages(parsed) {
  const out = collectNavPages(parsed.navigation);
  collectNavPages(parsed.navbar?.links, out);
  if (parsed.navbar?.primary) collectNavPages(parsed.navbar.primary, out);
  collectNavPages(parsed.footer?.links, out);
  for (const redirect of parsed.redirects ?? []) pushNavSlug(redirect?.destination, out);
  return out;
}

function navPageExists(slug) {
  const candidates = [`${slug}.mdx`, `${slug}.md`, `${slug}/index.mdx`, `${slug}/index.md`];
  return candidates.some((rel) => existsSync(join(ROOT, rel)));
}

function assertDocsConfig(docsJson) {
  let parsed;
  try {
    parsed = JSON.parse(docsJson);
  } catch {
    fail('docs.json is not JSON');
    return;
  }
  const tabs = parsed.navigation?.tabs;
  if (!Array.isArray(tabs)) {
    fail('docs.json navigation must be `navigation.tabs` (one tab per application)');
  } else {
    const labels = tabs.map((tab) => tab?.tab);
    for (const product of PRODUCT_TABS) {
      if (!labels.includes(product)) fail(`docs.json navigation.tabs must carry a "${product}" tab`);
    }
    for (const tab of tabs) {
      if (!tab?.icon) fail(`docs.json tab "${tab?.tab}" has no icon`);
      for (const group of tab?.groups ?? []) {
        if (!group?.icon) fail(`docs.json group "${group?.group}" in tab "${tab?.tab}" has no icon`);
      }
    }
  }
  if (parsed.theme !== 'mint') fail('docs.json theme must be "mint" (the Mintlify starter theme)');
  if (!parsed.favicon) fail('docs.json must set a favicon');
  for (const mode of ['light', 'dark']) {
    if (typeof parsed.logo?.[mode] !== 'string') fail(`docs.json logo.${mode} is missing`);
  }
  assertPublicApiNav(parsed);
  assertNavPagesExist(parsed);
}

function assertPublicApiNav(parsed) {
  const pages = navPages(parsed);
  for (const page of FORBIDDEN_AUTH_PAGES) {
    if (pages.includes(page)) {
      fail(
        `docs.json navigation must not list ${page} (public docs have no auth stack)`,
      );
    }
  }
}

function assertNavPagesExist(parsed) {
  const seen = new Set();
  for (const slug of navPages(parsed)) {
    if (seen.has(slug)) continue;
    seen.add(slug);
    if (!navPageExists(slug)) {
      fail(
        `docs.json nav href or page ${slug} has no matching MDX at ${slug}.mdx`,
      );
    }
  }
}

const AUTH_INTERNALS = [
  { pattern: /\/auth\//, label: '/auth/' },
  { pattern: /\/oauth\//, label: '/oauth/' },
  { pattern: /refresh_token/, label: 'refresh_token' },
  { pattern: /cortex_rt/, label: 'cortex_rt cookie internals' },
  { pattern: /\bWorkOS\b/, label: 'WorkOS' },
  { pattern: /client_secret/i, label: 'client secret' },
];

function assertNoAuthInternals(rel, text) {
  if (!rel.endsWith('.mdx')) return;
  for (const { pattern, label } of AUTH_INTERNALS) {
    if (pattern.test(text)) {
      fail(
        `${rel} exposes ${label} (docs.cortex.foundation is end-user; no auth stack)`,
      );
    }
  }
}

const IMAGES = [
  { pattern: /<img\b/i, label: '<img>' },
  { pattern: /<Frame\b/, label: '<Frame>' },
  { pattern: /!\[[^\]]*\]\(/, label: 'a markdown image' },
  { pattern: /^image:/m, label: '`image:` frontmatter' },
  { pattern: /\/images\//, label: 'an /images/ path' },
];

function assertNoImages(rel, text) {
  if (!rel.endsWith('.mdx')) return;
  for (const { pattern, label } of IMAGES) {
    if (pattern.test(text)) {
      fail(`${rel} uses ${label}; this site carries no images, use icons`);
    }
  }
}

function frontmatter(text) {
  const m = /^---\n([\s\S]*?)\n---\n/.exec(text);
  if (m === null) return null;
  const out = {};
  for (const line of m[1].split('\n')) {
    const kv = /^([a-zA-Z]+):\s*(.*)$/.exec(line);
    if (kv) out[kv[1]] = kv[2].replace(/^"(.*)"$/, '$1').replace(/^'(.*)'$/, '$1');
  }
  return out;
}

function assertFrontmatter(rel, text, titles) {
  if (!rel.endsWith('.mdx')) return;
  const fm = frontmatter(text);
  if (fm === null) {
    fail(`${rel} has no frontmatter`);
    return;
  }
  if (!fm.title) fail(`${rel} has no title`);
  if (!fm.description) fail(`${rel} has no description`);
  else if (fm.description.length > 160) fail(`${rel} description is ${fm.description.length} characters (max 160)`);
  if (!rel.startsWith('problems/') && !fm.icon) fail(`${rel} has no icon (this site uses icons, not images)`);
  if (fm.title) {
    const other = titles.get(fm.title);
    if (other !== undefined) fail(`${rel} repeats the title "${fm.title}" of ${other}`);
    else titles.set(fm.title, rel);
  }
}

function internalHrefs(text) {
  const body = text.replace(/```[\s\S]*?```/g, '');
  const out = new Set();
  for (const m of body.matchAll(/(?:href=|\]\()"?(\/[A-Za-z0-9._\-/#?=]*)"?/g)) {
    const raw = m[1].split('#')[0].split('?')[0];
    if (raw === '/' || raw === '') continue;
    out.add(raw.replace(/^\//, '').replace(/\/$/, ''));
  }
  return out;
}

function routerPaths(source) {
  const registered = new Set();
  for (const m of source.matchAll(/\.route\(\s*"([^"]+)"/g)) {
    const path = m[1];
    if (OPERATIONAL.has(path)) registered.add(path);
    else registered.add(`/v1${path}`);
  }
  return registered;
}

function normalizePath(path) {
  return path.replace(/\{[^}]+\}/g, '{}');
}

function documentedV1Paths(text) {
  const found = new Set();
  // Fenced examples (RFC 9457 documents, request bodies) are not the route
  // table. Inline backticks and markdown tables are.
  const withoutFences = text.replace(/```[\s\S]*?```/g, '');
  for (const tick of withoutFences.matchAll(/`([^`]+)`/g)) {
    const chunk = tick[1];
    for (const m of chunk.matchAll(/\/v1\/[A-Za-z0-9._~/{}\-]+/g)) {
      let path = m[0].replace(/[),.;]+$/g, '');
      if (path.includes('*') || path.includes('…')) continue;
      if (path === '/v1' || path === '/v1/') continue;
      if (path.endsWith('/')) path = path.slice(0, -1);
      if (/\/v1\/\{?$/.test(path)) continue;
      found.add(path);
    }
  }
  return found;
}

const errorRs = BACKEND === null ? '' : read('crates/cortex-core/src/error.rs', BACKEND);
const errorsTs = BACKEND === null ? '' : read('packages/api-types/src/errors.ts', BACKEND);
const routerRs = BACKEND === null ? '' : read('crates/cortex-api/src/router.rs', BACKEND);
const docsRoot = ROOT;

if (BACKEND !== null) {
  const rustBase = rustProblemBase(errorRs);
  const tsBase = tsProblemBase(errorsTs);
  if (rustBase === null) {
    fail('could not find `PROBLEM_TYPE_BASE` in crates/cortex-core/src/error.rs');
  } else if (rustBase !== EXPECTED_BASE) {
    fail(
      `PROBLEM_TYPE_BASE in error.rs is ${rustBase}; user-facing problem URIs must be ${EXPECTED_BASE}`,
    );
  }
  if (tsBase === null) {
    fail('could not find `PROBLEM_TYPE_BASE` in packages/api-types/src/errors.ts');
  } else if (tsBase !== rustBase && rustBase !== null) {
    fail(
      `PROBLEM_TYPE_BASE: error.rs serves ${rustBase} and api-types claims ${tsBase}`,
    );
  } else if (tsBase !== EXPECTED_BASE) {
    fail(
      `PROBLEM_TYPE_BASE in api-types is ${tsBase}; user-facing problem URIs must be ${EXPECTED_BASE}`,
    );
  }
}

const problemDir = join(docsRoot, 'problems');
const problemPages = existsSync(problemDir)
  ? readdirSync(problemDir).filter((name) => name.endsWith('.mdx') && name !== 'index.mdx')
  : [];
const pageCodes = new Set(problemPages.map((name) => name.replace(/\.mdx$/, '')));
const codes = BACKEND === null ? [...pageCodes] : rustErrorCodes(errorRs);
if (codes.length === 0) fail('no problem codes found');

for (const code of codes) {
  const rel = `problems/${code}.mdx`;
  if (!pageCodes.has(code)) {
    fail(`ErrorCode \`${code}\` has no Mintlify page at ${rel}`);
    continue;
  }
  const page = read(rel);
  const expectedType = `${EXPECTED_BASE}/${code}`;
  if (!page.includes(expectedType)) {
    fail(`${rel} does not state \`type\` ${expectedType}`);
  }
}
for (const extra of pageCodes) {
  if (!codes.includes(extra)) {
    fail(
      `problems/${extra}.mdx documents a code that is not in ErrorCode::as_str`,
    );
  }
}

if (!existsSync(join(docsRoot, 'docs.json'))) {
  fail('docs.json is missing (Mintlify site config)');
} else {
  const docsJson = read('docs.json');
  if (!docsJson.includes('docs.cortex.foundation')) {
    fail('docs.json must name docs.cortex.foundation');
  }
  if (docsJson.includes('docs.cortex.sh')) {
    fail('docs.json still names docs.cortex.sh');
  }
  assertDocsConfig(docsJson);
}

for (const rel of FORBIDDEN_AUTH_PAGES) {
  if (existsSync(join(docsRoot, `${rel}.mdx`))) {
    fail(
      `${rel}.mdx must not exist (sign in via the app; no auth/OAuth internals)`,
    );
  }
}

const registered = routerPaths(routerRs);
const registeredNorm = new Set([...registered].map(normalizePath));
const docsFiles = walk(docsRoot).filter((path) => /\.(mdx|md|json)$/.test(path));
const titles = new Map();

for (const file of docsFiles) {
  const rel = relative(ROOT, file).split('\\').join('/');
  if (rel === 'README.md' || rel === 'AGENTS.md') continue;
  const text = readFileSync(file, 'utf8');
  if (text.includes('docs.cortex.sh')) {
    fail(`${rel} names docs.cortex.sh (problem URIs belong on docs.cortex.foundation)`);
  }
  assertNoAuthInternals(rel, text);
  assertNoImages(rel, text);
  assertFrontmatter(rel, text, titles);
  if (rel.endsWith('.mdx')) {
    for (const slug of internalHrefs(text)) {
      if (!navPageExists(slug)) fail(`${rel} links to /${slug}, which has no MDX page`);
    }
  }
  if (BACKEND === null) continue;
  for (const path of documentedV1Paths(text)) {
    const norm = normalizePath(path);
    if (!registeredNorm.has(norm)) {
      fail(
        `${rel} documents \`${path}\`, which is not registered in crates/cortex-api/src/router.rs`,
      );
    }
  }
}

if (failures.length > 0) {
  console.error('\ncheck-docs-site: failed\n');
  for (const message of failures) console.error(`  - ${message}`);
  console.error('');
  process.exit(1);
}

console.log(
  `check-docs-site: ok (${codes.length} problem pages; ${
    BACKEND === null ? 'site-only, backend contract not checked' : `${registered.size} router paths`
  })`,
);
