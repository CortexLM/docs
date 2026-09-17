import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../../', import.meta.url));
const manifest = JSON.parse(readFileSync(join(root, 'design/docs-images.json'), 'utf8'));
const shots = new Map(manifest.shots.map((shot) => [shot.name, shot]));
const wallpapers = new Set(manifest.wallpapers.map((wallpaper) => wallpaper.name));
assert.equal(shots.size, manifest.shots.length, 'shot names must be unique');
assert.equal(new Set(manifest.shots.map((shot) => shot.node)).size, shots.size, 'Paper compositions must be unique');

for (const shot of manifest.shots) {
  assert.match(shot.name, /^[a-z0-9]+(?:-[a-z0-9]+)*$/);
  assert.ok(shot.source && shot.node, `${shot.name} must retain its Paper provenance`);
  assert.ok(wallpapers.has(shot.wallpaper), `${shot.name} must use a registered wallpaper`);
}

function* pages(directory) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    if (entry.name.startsWith('.') || entry.name === 'node_modules') continue;
    const path = join(directory, entry.name);
    if (entry.isDirectory()) yield* pages(path);
    else if (entry.name.endsWith('.mdx')) yield path;
  }
}

const used = new Set();
let pageCount = 0;
let frameCount = 0;
for (const path of pages(root)) {
  const text = readFileSync(path, 'utf8');
  const matches = [...text.matchAll(/src=["']\/images\/product\/([a-z0-9-]+)\.webp["']/g)];
  if (matches.length === 0) continue;
  pageCount++;
  frameCount += (text.match(/<Frame\b/g) || []).length;
  for (const [, name] of matches) {
    const shot = shots.get(name);
    assert.ok(shot, `${path}: ${name} needs a provenance entry`);
    assert.ok(!shot.galleryOnly, `${path}: ${name} is gallery-only: ${shot.galleryOnly}`);
    used.add(name);
    const data = readFileSync(join(root, 'images/product', `${name}.webp`));
    assert.equal(data.toString('ascii', 0, 4), 'RIFF', `${name}: invalid WebP container`);
    assert.equal(data.toString('ascii', 8, 12), 'WEBP', `${name}: invalid WebP signature`);
    assert.ok(data.length > 1000, `${name}: empty or truncated export`);
  }
}

for (const filename of readdirSync(join(root, 'images/product'))) {
  assert.ok(filename.endsWith('.webp'), `unexpected product asset: ${filename}`);
  const name = filename.slice(0, -5);
  assert.ok(used.has(name), `unused or gallery-only public asset: ${filename}`);
}

console.log(`docs-images: ${shots.size} Paper compositions, ${used.size} public assets, ${pageCount} pages, ${frameCount} frames passed`);
