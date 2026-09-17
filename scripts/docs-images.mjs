import { realpathSync, statSync } from 'node:fs';
import { isAbsolute, join, relative, resolve, sep } from 'node:path';

const IMAGE_ATTRIBUTES = new Set([
  'src', 'alt', 'width', 'height', 'className', 'loading', 'decoding', 'title',
]);
const MEDIA_TAGS = new Set([
  'image', 'picture', 'source', 'video', 'audio', 'iframe', 'embed', 'object', 'svg',
]);

function inside(directory, file) {
  const path = relative(directory, file);
  return path !== '' && path !== '..' && !path.startsWith(`..${sep}`) && !isAbsolute(path);
}

function imagePathError(root, src) {
  if (!src?.startsWith('/images/product/') ||
      !/^\/images\/product\/(?:[a-z0-9][a-z0-9_-]*\/)*[a-z0-9][a-z0-9._-]*\.(?:webp|png|jpe?g)$/i.test(src)) {
    return 'image src must be a safe local /images/product/ path ending in WebP, PNG or JPG (no remote URLs, escapes, queries or fragments)';
  }
  const file = resolve(root, src.slice(1));
  try {
    // Resolve the target too: a symlink must not turn a local URL into an escape.
    const directory = join(realpathSync(root), 'images', 'product');
    if (!inside(directory, realpathSync(file))) {
      return `unsafe image path outside images/product/: ${src}`;
    }
    const stat = statSync(file);
    if (!stat.isFile() || stat.size === 0) return `image path must name a nonempty file: ${src}`;
  } catch {
    return `missing or unreadable local image: ${src}`;
  }
  return null;
}

function hasAltText(value) {
  const decoded = (value ?? '')
    .replace(/&#(x[0-9a-f]+|\d+);/gi, (_, code) => {
      const number = code[0].toLowerCase() === 'x' ? parseInt(code.slice(1), 16) : Number(code);
      return number > 0 && number <= 0x10ffff ? String.fromCodePoint(number) : '';
    })
    .replace(/&(?:nbsp|ensp|emsp|thinsp|hairsp|Tab|NewLine|ZeroWidthSpace);/gi, ' ');
  return decoded.replace(/[\s\p{C}]/gu, '').length > 0;
}

function mask(text) {
  return text.replace(/[^\n]/g, ' ');
}

function imageMarkup(text) {
  // Code samples and comments do not load media. Preserve offsets for diagnostics.
  return text
    .replace(/^ {0,3}(`{3,}|~{3,})[^\n]*\n[\s\S]*?^ {0,3}\1[ \t]*(?=\n|$)/gm, mask)
    .replace(/(`+)[^\n]*?\1/g, mask)
    .replace(/<!--[\s\S]*?-->|{\/\*[\s\S]*?\*\/}/g, mask);
}

/** Check the intentionally narrow, literal <img /> syntax used by product docs. */
export function checkProductImages(text, root) {
  const errors = [];
  const normalized = text.replace(/\r/g, '');
  const frontmatter = /^---\n([\s\S]*?)\n---(?:\n|$)/.exec(normalized);
  if (frontmatter && /^\s*(?:image|"image"|'image')\s*:/mi.test(frontmatter[1])) {
    errors.push('image frontmatter is unsupported; use an accessible local <img /> in the article');
  }
  const body = imageMarkup(frontmatter ? mask(frontmatter[0]) + normalized.slice(frontmatter[0].length) : normalized);
  if (/(?<!\\)!\[/.test(body)) {
    errors.push('markdown images are unsupported; use a literal local <img /> with alt text');
  }

  // Scan tags with quoted values intact, including multiline attributes and ">" in alt text.
  const tags = /<(\/?)([A-Za-z][\w.:-]*)(?=[\s/>])/g;
  for (let match; (match = tags.exec(body));) {
    const [, closing, name] = match;
    let end = tags.lastIndex;
    let quote = null;
    for (; end < body.length; end++) {
      const char = body[end];
      if (quote) {
        if (char === quote) quote = null;
      } else if (char === '"' || char === "'") {
        quote = char;
      } else if (char === '>' || char === '<') {
        break;
      }
    }
    const lower = name.toLowerCase();
    const label = `image at line ${body.slice(0, match.index).split('\n').length}`;
    const fail = (message) => errors.push(`${label}: ${message}`);
    const attributes = body.slice(tags.lastIndex, end);
    tags.lastIndex = end;
    if (lower !== 'img') {
      if (!closing && (MEDIA_TAGS.has(lower) ||
          /\b(?:src|srcset|poster|image|img)\s*=/i.test(attributes))) {
        fail(`unsupported media <${name}>; use a local <img />, optionally wrapped in <Frame>`);
      }
      continue;
    }
    if (name !== 'img' || closing || body[end] !== '>' || !/\/\s*$/.test(attributes)) {
      fail('use a self-closing lowercase <img /> with literal quoted attributes');
      continue;
    }
    const source = attributes.replace(/\/\s*$/, '');
    const attribute = /\s+([A-Za-z][\w-]*)\s*=\s*(?:"([^"]*)"|'([^']*)')/y;
    const values = new Map();
    let position = 0;
    while (position < source.length) {
      if (!source.slice(position).trim()) break;
      attribute.lastIndex = position;
      const item = attribute.exec(source);
      if (!item) {
        fail('image attributes must be literal quoted values; no expressions or spreads');
        break;
      }
      const [, key, double, single] = item;
      if (!IMAGE_ATTRIBUTES.has(key)) fail(`unsupported image attribute ${key}`);
      if (values.has(key)) fail(`duplicate image attribute ${key}`);
      values.set(key, double ?? single);
      position = attribute.lastIndex;
    }
    if (!hasAltText(values.get('alt'))) fail('image alt text must be nonempty');
    const pathError = imagePathError(root, values.get('src'));
    if (pathError) fail(pathError);
    for (const dimension of ['width', 'height']) {
      if (values.has(dimension) && !/^[1-9]\d*$/.test(values.get(dimension))) {
        fail(`image ${dimension} must be a positive integer`);
      }
    }
    if (values.has('className') && !/^[\w:\s-]+$/.test(values.get('className'))) {
      fail('image className must contain plain class names, not styles or media URLs');
    }
    if (values.has('loading') && !['lazy', 'eager'].includes(values.get('loading'))) {
      fail('image loading must be lazy or eager');
    }
    if (values.has('decoding') && !['async', 'sync', 'auto'].includes(values.get('decoding'))) {
      fail('image decoding must be async, sync or auto');
    }
  }
  return errors;
}
