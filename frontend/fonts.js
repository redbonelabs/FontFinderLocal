// Bounded, lazy font loading. Unique family aliases prevent name collisions.
const assets = new Map();
const queue = [];
let active = 0;
export const alias = font => `ff_${font.id.replaceAll('-', '_')}`;
const present = id => document.querySelector(`[data-font-id="${id}"]`);

function trim() {
  for (const [id, entry] of assets) {
    if (assets.size <= 80) break;
    if (entry.face && !present(id)) {
      document.fonts.delete(entry.face);
      assets.delete(id);
    }
  }
}

function pump() {
  while (active < 4 && queue.length) {
    const job = queue.shift();
    if (!present(job.font.id)) {
      assets.delete(job.font.id);
      job.reject(new Error('Preview left the viewport.'));
      continue;
    }
    active++;
    const face = new FontFace(alias(job.font), `url("/api/fonts/${job.font.id}/asset")`);
    face.load().then(loaded => {
      document.fonts.add(loaded);
      const entry = assets.get(job.font.id);
      if (entry) entry.face = loaded;
      job.resolve(loaded);
      trim();
    }).catch(() => {
      assets.delete(job.font.id);
      job.reject(new Error('This font could not be rendered. Try rescanning fonts.'));
    }).finally(() => { active--; pump(); });
  }
}

function load(font) {
  if (assets.has(font.id)) {
    const entry = assets.get(font.id);
    assets.delete(font.id);
    assets.set(font.id, entry);
    return entry.promise;
  }
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  assets.set(font.id, {promise});
  queue.push({font, resolve, reject});
  queueMicrotask(pump);
  return promise;
}

export function missingCharacters(font, text) {
  return [...new Set([...text])].filter(char => {
    const cp = char.codePointAt(0);
    if (/\s/u.test(char) || cp === 0x200d || cp === 0x200c || (cp >= 0xfe00 && cp <= 0xfe0f)) return false;
    let lo = 0, hi = font.coverage.length - 1;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1, [start, end] = font.coverage[mid];
      if (cp < start) hi = mid - 1;
      else if (cp > end) lo = mid + 1;
      else return false;
    }
    return true;
  });
}

export function updateSample(container, font, text, size, coordinates = {}) {
  const sample = container.querySelector('.font-sample');
  const status = container.querySelector('.render-status');
  sample.textContent = text;
  sample.style.fontSize = `${size}px`;
  sample.style.fontFamily = `"${alias(font)}"`;
  const values = {...Object.fromEntries(font.axes.map(a => [a.tag, a.default])), ...coordinates};
  // OpenType tags are constrained before interpolation into CSS.
  sample.style.fontVariationSettings = Object.entries(values)
    .filter(([tag, value]) => /^[\x20-\x7e]{4}$/.test(tag) && !/["\\]/.test(tag) && Number.isFinite(value))
    .map(([tag, value]) => `"${tag}" ${value}`).join(', ') || 'normal';
  const missing = missingCharacters(font, text);
  if (container.dataset.loaded === 'true') {
    status.className = `render-status${missing.length ? ' warning' : ''}`;
    status.textContent = missing.length ? `Missing ${missing.length} character${missing.length === 1 ? '' : 's'}: ${missing.slice(0, 8).join(' ')} — these may use fallback` : (text ? '' : 'Enter preview text above.');
  }
}

export function createSample(container, font, text, size, coordinates = {}) {
  container.dataset.fontId = font.id;
  const sample = document.createElement('div');
  sample.className = 'font-sample loading';
  const status = document.createElement('div');
  status.className = 'render-status';
  status.textContent = 'Loading font asset…';
  container.append(sample, status);
  updateSample(container, font, text, size, coordinates);
  // Defer until the caller attaches the card to the DOM.
  queueMicrotask(async () => {
    try {
      await load(font);
      await document.fonts.load(`16px "${alias(font)}"`);
      if (!container.isConnected) return;
      container.dataset.loaded = 'true';
      sample.classList.remove('loading');
      const currentVariations = sample.style.fontVariationSettings;
      updateSample(container, font, sample.textContent, parseInt(sample.style.fontSize), coordinates);
      sample.style.fontVariationSettings = currentVariations;
    } catch (error) {
      if (!container.isConnected) return;
      sample.classList.add('loading');
      status.textContent = error.message;
      status.className = 'render-status error';
    }
  });
}
