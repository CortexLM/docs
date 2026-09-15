import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const root = new URL('../../', import.meta.url);
const config = JSON.parse(readFileSync(new URL('docs.json', root), 'utf8'));
assert.equal(config.theme, 'willow');
assert.deepEqual(config.navbar.links, [
  { label: 'Home', href: '/' },
  { label: 'Documentation', href: '/getting-started/quickstart' },
]);
assert.equal(config.navbar.primary, undefined);
for (const mode of ['light', 'dark']) {
  const file = new URL(config.logo[mode].replace(/^\//, ''), root);
  assert.equal(readFileSync(file).subarray(0, 8).toString('hex'), '89504e470d0a1a0a');
}
assert.equal(config.icons.library, 'lucide');

// The sidebar is one flat list of top-level groups. `tabs`, `dropdowns` and
// `products` each render a second-level switcher in the navbar — the app
// dropdown this site deliberately dropped — so a group-only navigation is the
// contract, not a preference.
assert.equal(config.navigation.tabs, undefined);
assert.equal(config.navigation.dropdowns, undefined);
assert.equal(config.navigation.products, undefined);
assert.ok(Array.isArray(config.navigation.groups));
assert.ok(
  config.navigation.groups.every(group => typeof group.group === 'string' && group.icon),
  'every top-level group needs a label and an icon',
);
// One hub per product: the group that opens a product starts at its hub page,
// so the sidebar title and the entry point are the same page.
for (const hub of [
  ['Chat', 'chat/index'],
  ['Code', 'code/index'],
  ['Bot', 'bot/index'],
  ['CLI', 'cli/index'],
  ['Design', 'design/index'],
]) {
  const [label, root] = hub;
  const group = config.navigation.groups.find(candidate => candidate.group === label);
  assert.ok(group, `navigation must carry a top-level "${label}" group`);
  assert.equal(group.root, root, `"${label}" must open ${root}`);
}
assert.deepEqual(config.footer.links.map(group => group.header), ['Products', 'Resources', 'Cortex']);
console.log('docs-ui: native theme, flat hub sidebar, logos, icons and footer passed');
