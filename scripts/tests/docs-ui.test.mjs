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
assert.ok(config.navigation.tabs.every(tab => tab.groups.every(group => group.icon)));
assert.deepEqual(config.footer.links.map(group => group.header), ['Products', 'Resources', 'Cortex']);
console.log('docs-ui: native theme, navbar, logos, icons and footer passed');
