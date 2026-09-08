#!/usr/bin/env node
/**
 * Checks the public Mintlify site. Pass a backend checkout as the first
 * argument to also check the API contract and registered routes.
 *
 * # Why this exists
 *
 * `PROBLEM_TYPE_BASE` is wire contract. It used to point at
 * `docs.cortex.sh/problems`, a host that did not serve pages and is not the
 * product domain. Moving it without pages, or documenting `/v1/…` paths the
 * router does not register, is the same class of silent decay as an unmirrored
 * `ErrorCode`.
 *
 * This check is mechanical rather than a note in a contributing guide because
 * the note is what would be ignored the next time someone adds a code or a
 * "helpful" endpoint to a docs table. It also holds the top navbar to Home +
 * Documentation (not Chat | Code | Bot product chrome) and home CTAs to ink,
 * not a brand-green Install / `navbar.primary` button. Public MDX must not
 * document `/auth/`, `/oauth/`, refresh tokens, WorkOS, or `cortex_rt`. A
 * `docs.json` navigation entry must resolve to an MDX page — Mintlify will
 * otherwise publish a sidebar link that 404s, and the rest of this job would
 * still pass.
 *
 * Kubernetes labels and AWS tags under `deploy/` that use `cortex.sh/…` are
 * internal identifiers and are not scanned.
 */

import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(process.env.CORTEX_CHECK_ROOT ?? fileURLToPath(new URL('..', import.meta.url)));
const BACKEND = process.argv[2] === undefined ? null : resolve(process.argv[2]);
const EXPECTED_BASE = 'https://docs.cortex.foundation/problems';
const OPERATIONAL = new Set(['/healthz', '/readyz', '/startupz']);

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

const PRODUCT_CHROME = new Set(['Chat', 'Code', 'Bot', 'Design']);

function assertDocsChrome(docsJson) {
  let parsed;
  try {
    parsed = JSON.parse(docsJson);
  } catch {
    fail('docs.json is not JSON');
    return;
  }
  const links = parsed.navbar?.links;
  if (!Array.isArray(links)) {
    fail('docs.json navbar.links must include Home and Documentation');
    return;
  }
  const labels = links.map((link) => link?.label);
  if (!labels.includes('Home') || !labels.includes('Documentation')) {
    fail('docs.json navbar must be Home + Documentation, not product chrome');
  }
  for (const label of labels) {
    if (typeof label === 'string' && PRODUCT_CHROME.has(label)) {
      fail(
        `docs.json navbar.links must not include product chrome "${label}" (those are documentation tabs)`,
      );
    }
  }
  if (parsed.navbar?.primary) {
    fail(
      'docs.json navbar.primary is a brand-green CTA; docs CTAs are ink, not Install',
    );
  }
  assertPublicApiNav(parsed);
  assertNavPagesExist(parsed);
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
 * object. `href` on navbar links and nav objects is the same contract: an
 * internal path must resolve to MDX. Walking only `pages` strings is how a
 * dead navbar `/missing-mintlify-page` href used to leave this job green.
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
  return out;
}

function navPageExists(slug) {
  const candidates = [`${slug}.mdx`, `${slug}.md`, `${slug}/index.mdx`, `${slug}/index.md`];
  return candidates.some((rel) => existsSync(join(ROOT, rel)));
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
  assertDocsChrome(docsJson);
}

for (const rel of FORBIDDEN_AUTH_PAGES) {
  if (existsSync(join(docsRoot, `${rel}.mdx`))) {
    fail(
      `${rel}.mdx must not exist (sign in via the app; no auth/OAuth internals)`,
    );
  }
}

const indexMdx = join(docsRoot, 'index.mdx');
if (existsSync(indexMdx)) {
  const index = readFileSync(indexMdx, 'utf8');
  if (/<Card\s[^>]*title="(Quickstart|Download|Install)"/.test(index)) {
    fail(
      'index.mdx must not use a Mintlify Card as a brand-green home CTA',
    );
  }
  if (/\b(Quickstart|Download Cortex)\b/.test(index) && !index.includes('ink-btn')) {
    fail('index.mdx home CTAs must use ink-btn, not Mintlify primary Cards');
  }
  if (!existsSync(join(docsRoot, 'custom.css'))) {
    fail('custom.css is missing (ink CTA styles)');
  }
}

const registered = routerPaths(routerRs);
const registeredNorm = new Set([...registered].map(normalizePath));
const docsFiles = walk(docsRoot).filter((path) => /\.(mdx|md|json)$/.test(path));

for (const file of docsFiles) {
  const rel = relative(ROOT, file);
  const text = readFileSync(file, 'utf8');
  if (text.includes('docs.cortex.sh')) {
    fail(`${rel} names docs.cortex.sh (problem URIs belong on docs.cortex.foundation)`);
  }
  if (rel.endsWith('.mdx') && text.includes('/images/frames/')) {
    fail(
      `${rel} uses a retired fake-app SVG plate under /images/frames/; use images/product/*.png or images/cli/`,
    );
  }
  assertNoAuthInternals(rel, text);
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
