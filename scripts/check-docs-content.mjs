#!/usr/bin/env node
/**
 * Content checks for the documentation tree.
 *
 * `check-docs-site.mjs` checks the site's shape: that `docs.json` and the MDX tree agree
 * both ways, that the problem pages match the backend's error enum, that no image or
 * sign-in internal has crept in, and that every page has frontmatter. This script checks
 * what is inside a page:
 *
 *   - frontmatter completeness, the 160-character description ceiling Mintlify renders
 *     into meta tags, and titles that are unique across the site
 *   - the forbidden-vocabulary list: sign-in wire internals, image paths, third-party
 *     vendor and competitor names, and emoji
 *   - `/v1/` API paths, which belong only on the pages that document the API
 *   - internal links resolving to a real page, and external links staying inside the
 *     allowlist
 *   - every page closing with a "## Related" (or "## Next") section, so no page is a
 *     dead end, and carrying enough prose to be worth landing on
 *   - balanced MDX components, `icon=` on every `<Card>`, and a `<CardGroup>` on every
 *     section landing page
 *
 * Usage:
 *   node scripts/check-docs-content.mjs                 every page in docs.json
 *   node scripts/check-docs-content.mjs cli/headless     one page (slug, no .mdx)
 *
 * Exits 1 on any failure, one line per failure: "<slug>: <message>".
 */
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(process.env.CORTEX_CHECK_ROOT ?? fileURLToPath(new URL('..', import.meta.url)));

const FORBIDDEN = [
  // Sign-in wire internals. The public docs describe what a person does, never the
  // protocol underneath it.
  [/\/auth\//, 'auth path'],
  [/\/oauth\//, 'oauth path'],
  [/refresh_token/, 'refresh_token'],
  [/cortex_rt/, 'cortex_rt'],
  [/\bWorkOS\b/, 'WorkOS'],
  [/client_secret/i, 'client_secret'],
  [/docs\.cortex\.sh/, 'docs.cortex.sh'],
  // No images anywhere in this site, by design.
  [/\/images\//, 'image path'],
  [/<img\b/i, '<img>'],
  [/<Frame\b/, '<Frame>'],
  [/!\[[^\]]*\]\(/, 'markdown image'],
  [/^image:/m, 'image frontmatter'],
  // Competitors and third-party vendors. Cortex documentation describes Cortex.
  [/\bChatGPT\b/, 'competitor: ChatGPT'],
  [/\bOpenAI\b/, 'competitor: OpenAI'],
  [/\bClaude\b/, 'competitor: Claude'],
  [/\bAnthropic\b/, 'competitor: Anthropic'],
  [/\bGemini\b/, 'competitor: Gemini'],
  [/\bCopilot\b/, 'competitor: Copilot'],
  // "Cursor" is also a real interface noun, so the common noun uses are excused.
  [/\bCursor\b(?! (?:keys|position|movement|blink|is|to|and|at|in|on|over|left|right|up|down))/, 'competitor: Cursor'],
  [/\bCodex\b/, 'competitor: Codex'],
  [/\bGrok\b/, 'Grok'],
  [/\bQwen\b/, 'vendor: Qwen'],
  [/\bLlama\b/, 'vendor: Llama'],
  [/\bMistral\b/, 'vendor: Mistral'],
  [/\bvLLM\b/, 'vendor: vLLM'],
  [/\bSGLang\b/, 'vendor: SGLang'],
  [/\bGroq\b/, 'vendor: Groq'],
  [/\bPolly\b/, 'vendor: Polly'],
  [/\bComposio\b/, 'vendor: Composio'],
  [/\bPipedream\b/, 'vendor: Pipedream'],
  [/\bStripe\b/, 'vendor: Stripe'],
  [/\bAWS\b/, 'vendor: AWS'],
  [/\bFirecracker\b/, 'vendor: Firecracker'],
  [/\bgVisor\b/, 'vendor: gVisor'],
  [/\bRedis\b/, 'vendor: Redis'],
  [/\bPostgres(?:QL)?\b/, 'vendor: Postgres'],
  [/\bKubernetes\b/, 'vendor: Kubernetes'],
  [/\bHelm\b/, 'vendor: Helm'],
  [/\bTerraform\b/, 'vendor: Terraform'],
  [/\bCloudflare\b/, 'vendor: Cloudflare'],
  [/\bGreptile\b/, 'vendor: Greptile'],
  [/\bElectron\b/, 'vendor: Electron'],
  [/\bNext\.js\b/, 'vendor: Next.js'],
  [/\bSolidJS\b/, 'vendor: SolidJS'],
  [/\bReact\b/, 'vendor: React'],
  [/\bDataCrunch\b/i, 'vendor: DataCrunch'],
  [/\bVerda\b/, 'vendor: Verda'],
  [/\bTailscale\b/, 'vendor: Tailscale'],
  [/\bOpenBao\b/, 'vendor: OpenBao'],
  // U+2660-U+2667 (card suits) are excluded from the emoji range: the terminal
  // interface draws the diamond as a row marker, so it is a product glyph inside a
  // quoted string, not decoration.
  [/[\u{1F300}-\u{1FAFF}\u{2600}-\u{265F}\u{2668}-\u{27BF}]/u, 'emoji'],
];

const COMPONENTS = [
  'Steps', 'Step', 'Tabs', 'Tab', 'AccordionGroup', 'Accordion', 'CardGroup', 'Card',
  'Note', 'Tip', 'Warning', 'Info', 'Check', 'Update',
];

const EXTERNAL_ALLOWED = [
  /^https:\/\/(?:[a-z0-9-]+\.)*cortex\.foundation/,
  /^https:\/\/github\.com\/CortexLM\//,
];

/** Every .mdx file in the tree, as a slug relative to the repository root. */
function mdxSlugs(dir = ROOT, out = new Set()) {
  for (const name of readdirSync(dir)) {
    if (name === 'node_modules' || name === 'scripts' || name.startsWith('.')) continue;
    const path = join(dir, name);
    if (statSync(path).isDirectory()) mdxSlugs(path, out);
    else if (name.endsWith('.mdx')) {
      out.add(relative(ROOT, path).replace(/\\/g, '/').replace(/\.mdx$/, ''));
    }
  }
  return out;
}

/** Page slugs reachable from docs.json navigation, in navigation order. */
function collectNavPages(node, out = []) {
  if (node == null) return out;
  if (typeof node === 'string') {
    if (!node.startsWith('http') && !out.includes(node)) out.push(node);
    return out;
  }
  if (Array.isArray(node)) {
    for (const item of node) collectNavPages(item, out);
    return out;
  }
  if (typeof node !== 'object') return out;
  // A group's `root` is the page its title opens, and it is not repeated in `pages`.
  if (typeof node.root === 'string') collectNavPages(node.root, out);
  if (Array.isArray(node.pages)) collectNavPages(node.pages, out);
  if (Array.isArray(node.groups)) collectNavPages(node.groups, out);
  if (Array.isArray(node.tabs)) collectNavPages(node.tabs, out);
  return out;
}

/**
 * Section landing pages, which need a <CardGroup> so the section has a visible index:
 * the site index and every `<section>/index` page, plus any navigation group whose `root`
 * is some other page. `problems/index` is excluded -- it indexes the error codes as a
 * table, not as cards.
 */
function landingPages(navigation, slugs) {
  const out = new Set(['index']);
  const visit = (node) => {
    if (node == null || typeof node !== 'object') return;
    if (Array.isArray(node)) { for (const item of node) visit(item); return; }
    if (typeof node.root === 'string') out.add(node.root);
    visit(node.pages);
    visit(node.groups);
    visit(node.tabs);
  };
  visit(navigation);
  for (const slug of slugs) if (slug.endsWith('/index')) out.add(slug);
  out.delete('problems/index');
  return out;
}

function frontmatter(text) {
  const m = /^---\n([\s\S]*?)\n---\n/.exec(text);
  if (!m) return null;
  const fm = {};
  for (const line of m[1].split('\n')) {
    const kv = /^([a-zA-Z]+):\s*(.*)$/.exec(line);
    if (kv) fm[kv[1]] = kv[2].replace(/^"(.*)"$/, '$1').replace(/^'(.*)'$/, '$1');
  }
  return { fm, body: text.slice(m[0].length) };
}

function checkPage(slug, ctx) {
  const out = [];
  const file = join(ROOT, `${slug}.mdx`);
  if (!existsSync(file)) return [`${slug}: MISSING FILE`];
  const text = readFileSync(file, 'utf8').replace(/\r/g, '');
  const parsed = frontmatter(text);
  if (!parsed) return [`${slug}: no frontmatter`];
  const { fm, body } = parsed;

  const isProblem = slug.startsWith('problems/');
  const isChangelog = slug === 'changelog';

  if (!fm.title) out.push('frontmatter: missing title');
  else {
    const prior = ctx.titles.get(fm.title);
    if (prior !== undefined && prior !== slug) {
      out.push(`frontmatter: title "${fm.title}" duplicates ${prior}`);
    }
    ctx.titles.set(fm.title, slug);
  }
  if (!fm.description) out.push('frontmatter: missing description');
  else if (fm.description.length > 160) {
    out.push(`frontmatter: description is ${fm.description.length} chars (max 160)`);
  }
  if (!isProblem && !fm.icon) out.push('frontmatter: missing icon');

  for (const [re, label] of FORBIDDEN) {
    const m = re.exec(text);
    if (m) {
      const line = text.slice(0, m.index).split('\n').length;
      const source = JSON.stringify(text.split('\n')[line - 1].slice(0, 100));
      out.push(`forbidden ${label} at line ${line}: ${source}`);
    }
  }

  // /v1 paths belong only on the pages that document the API. Whether a documented path
  // is actually registered is checked against the backend by check-docs-site.mjs.
  if (!ctx.apiPages.has(slug)) {
    const noFences = text.replace(/```[\s\S]*?```/g, '');
    for (const m of noFences.matchAll(/\/v1\/[A-Za-z0-9._~/{}\-]+/g)) {
      out.push(`API path ${m[0].replace(/[),.;]+$/g, '')} on a non-API page`);
    }
  }

  for (const m of body.matchAll(/(?:href=|\]\()"?(\/[A-Za-z0-9._\-/#?=]*)"?/g)) {
    const raw = m[1].split('#')[0].split('?')[0];
    if (raw === '/' || raw === '') continue;
    const target = raw.replace(/^\//, '').replace(/\/$/, '') || 'index';
    if (![target, `${target}/index`].some((c) => ctx.slugs.has(c))) {
      out.push(`link to /${target} has no page`);
    }
  }

  for (const m of body.matchAll(/https?:\/\/[^\s)"'<>\]]+/g)) {
    if (!EXTERNAL_ALLOWED.some((re) => re.test(m[0]))) {
      out.push(`external link outside the allowlist: ${m[0]}`);
    }
  }

  if (!isProblem && !isChangelog) {
    if (!/\n## (Related|Next)\b/.test(body)) {
      out.push('missing closing "## Related" (or "## Next") section');
    }
    const words = body.replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length;
    if (words < 250) out.push(`thin page: ${words} words`);
  }

  for (const tag of COMPONENTS) {
    const opens = (body.match(new RegExp(`<${tag}(?=[\\s>])(?![^>]*\\/>)`, 'g')) || []).length;
    const closes = (body.match(new RegExp(`</${tag}>`, 'g')) || []).length;
    if (opens !== closes) out.push(`unbalanced <${tag}>: ${opens} open, ${closes} close`);
  }

  // Every card carries an icon, because this site has no images to carry instead.
  for (const m of body.matchAll(/<Card\b[^>]*>/g)) {
    if (!/icon=/.test(m[0])) out.push(`<Card> without icon: ${m[0].slice(0, 80)}`);
  }

  if (ctx.landing.has(slug) && !/<CardGroup/.test(body)) {
    out.push('hub page without a <CardGroup>');
  }

  return out.map((s) => `${slug}: ${s}`);
}

const parsed = JSON.parse(readFileSync(join(ROOT, 'docs.json'), 'utf8'));
const navigation = collectNavPages(parsed.navigation);
const slugs = mdxSlugs();

const apiPages = new Set(['reference/errors', 'bounty/public-api']);
for (const slug of slugs) if (slug.startsWith('problems/')) apiPages.add(slug);

const ctx = {
  slugs,
  apiPages,
  landing: landingPages(parsed.navigation, slugs),
  titles: new Map(),
};

const args = process.argv.slice(2).map((a) => a.replace(/\.mdx$/, '').replace(/^\//, ''));
const targets = args.length ? args : navigation;

// Title uniqueness is a whole-site property, so a single-page run still needs every
// other page's title in hand before it can judge its own.
if (args.length) {
  for (const slug of navigation) {
    if (targets.includes(slug) || !existsSync(join(ROOT, `${slug}.mdx`))) continue;
    const p = frontmatter(readFileSync(join(ROOT, `${slug}.mdx`), 'utf8').replace(/\r/g, ''));
    if (p?.fm.title) ctx.titles.set(p.fm.title, slug);
  }
}

const failures = targets.flatMap((slug) => checkPage(slug, ctx));
if (failures.length) {
  console.error(failures.join('\n'));
  console.error(`\n${failures.length} problem(s)`);
  process.exit(1);
}
console.log(`check-docs-content: ok (${targets.length} page(s))`);
