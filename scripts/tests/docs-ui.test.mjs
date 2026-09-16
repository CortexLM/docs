import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

const root = new URL('../../', import.meta.url);
const config = JSON.parse(readFileSync(new URL('docs.json', root), 'utf8'));

// The site starts from the Mintlify starter kit: the `mint` theme, a favicon,
// a light and a dark logo, a navbar with links and one primary button, and
// contextual options. Icons come from Font Awesome (the starter default), so
// `icons.library` stays unset.
assert.equal(config.theme, 'mint');
assert.ok(typeof config.favicon === 'string' && existsSync(new URL(config.favicon.replace(/^\//, ''), root)));
for (const mode of ['light', 'dark']) {
  const file = new URL(config.logo[mode].replace(/^\//, ''), root);
  assert.ok(existsSync(file), `logo.${mode} must exist`);
  assert.ok(readFileSync(file, 'utf8').startsWith('<svg'), `logo.${mode} must be an SVG`);
}
assert.equal(config.icons, undefined, 'icons come from Font Awesome, the starter default');
assert.ok(Array.isArray(config.navbar.links) && config.navbar.links.length > 0);
assert.equal(config.navbar.primary?.type, 'button');
assert.equal(config.navbar.primary?.label, 'Open Cortex');
assert.ok(Array.isArray(config.contextual?.options) && config.contextual.options.includes('copy'));

// Navigation is one tab per application in the navbar, the way a reader picks
// a product on any large documentation site. Every tab and every group has an
// icon; every product tab opens on its hub page.
assert.ok(Array.isArray(config.navigation.tabs), 'navigation must be tabs');
assert.equal(config.navigation.groups, undefined);
assert.equal(config.navigation.dropdowns, undefined);
assert.equal(config.navigation.products, undefined);
const tabs = config.navigation.tabs.map((tab) => tab.tab);
assert.deepEqual(tabs, ['Get started', 'Chat', 'Code', 'Bot', 'CLI', 'Design', 'Security', 'Reference']);
for (const tab of config.navigation.tabs) {
  assert.ok(tab.icon, `tab "${tab.tab}" needs an icon`);
  assert.ok(Array.isArray(tab.groups) && tab.groups.length > 0, `tab "${tab.tab}" needs groups`);
  for (const group of tab.groups) {
    assert.ok(typeof group.group === 'string' && group.icon, `group "${group.group}" needs a label and an icon`);
    assert.ok(Array.isArray(group.pages) && group.pages.length > 0, `group "${group.group}" needs pages`);
  }
}
for (const [label, hub] of [
  ['Chat', 'chat/index'],
  ['Code', 'code/index'],
  ['Bot', 'bot/index'],
  ['CLI', 'cli/index'],
  ['Design', 'design/index'],
  ['Security', 'security/index'],
]) {
  const tab = config.navigation.tabs.find((candidate) => candidate.tab === label);
  assert.equal(tab.groups[0].pages[0], hub, `"${label}" must open on ${hub}`);
}
assert.equal(config.navigation.tabs[0].groups[0].pages[0], 'index', 'Get started opens on the home page');

// Global anchors and the footer keep the reader one click from the changelog,
// the status page, and the product.
const anchors = config.navigation.global.anchors.map((anchor) => anchor.href);
assert.ok(anchors.includes('/changelog'));
assert.ok(anchors.includes('https://status.cortex.foundation'));
assert.deepEqual(config.footer.links.map((group) => group.header), ['Products', 'Resources', 'Cortex']);

// No page ships an image: the site is icons only.
assert.ok(!existsSync(new URL('images', root)), 'the images/ directory must not exist');
assert.ok(!existsSync(new URL('custom.css', root)), 'custom.css is gone with the old ink CTAs');

console.log('docs-ui: starter theme, product tabs, icons, anchors and footer passed');
