// Bounded, lazy font loading. Unique family aliases prevent name collisions.
const assets = new Map();
const queue = [];
let active = 0;
export const alias = font => `ff_${font.id.replaceAll('-', '_')}`;
const present = id => document.querySelector(`[data-font-id="${id}"]`);
const sampleSettings = new WeakMap();
const metricsContext = document.createElement('canvas').getContext('2d');

function fitSample(sample, font, text, size) {
  let lineHeight = size * 1.2;
  const lines = text.split(/\r\n?|\n/);
  let above = 0, below = 0, left = 0, right = 0;
  let ascent = 0, descent = 0, baseline = size;
  const face = assets.get(font.id)?.face;
  if (face) {
    // FontFace defaults let canvas measure the same variable instance as the DOM.
    face.variationSettings = sample.style.fontVariationSettings;
    metricsContext.font = `${size}px "${alias(font)}"`;
    metricsContext.fontKerning = 'normal';
    metricsContext.textBaseline = 'alphabetic';
    for (const line of lines) {
      const m = metricsContext.measureText(line);
      ascent = Math.max(ascent, m.actualBoundingBoxAscent);
      descent = Math.max(descent, m.actualBoundingBoxDescent);
      lineHeight = Math.max(lineHeight, m.fontBoundingBoxAscent + m.fontBoundingBoxDescent);
      baseline = m.fontBoundingBoxAscent;
      left = Math.max(left, m.actualBoundingBoxLeft);
      right = Math.max(right, m.actualBoundingBoxRight - m.width);
    }
    lineHeight = Math.max(lineHeight, ascent + descent);
  }
  sample.style.lineHeight = `${lineHeight}px`;
  sample.style.padding = '8px 0 4px';
  // Browser inline metrics can differ from canvas metrics (notably in CFF and
  // fallback runs). Include the DOM line boxes, then measure the real baseline.
  if (sample.isConnected && sample.getClientRects().length) {
    const range = document.createRange(); range.selectNodeContents(sample);
    for (const rect of range.getClientRects()) lineHeight = Math.max(lineHeight, rect.height);
    sample.style.lineHeight = `${lineHeight}px`;
    const probe = document.createElement('span');
    probe.style.cssText = 'display:inline-block;width:0;height:0;vertical-align:baseline';
    sample.prepend(probe);
    baseline = probe.getBoundingClientRect().top - sample.getBoundingClientRect().top - 8;
    probe.remove();
  }
  if (face) {
    above = Math.max(0, ascent - baseline);
    below = Math.max(0, descent - (lineHeight - baseline));
  }
  // Keep the original visual padding, adding only measured ink overhang. Natural
  // height includes every line and the horizontal scrollbar; flex must not shrink it.
  sample.style.paddingTop = `${8 + Math.ceil(above)}px`;
  sample.style.paddingBottom = `${4 + Math.ceil(below)}px`;
  sample.style.paddingLeft = `${Math.ceil(left)}px`;
  sample.style.paddingRight = `${Math.ceil(right)}px`;
  sample.style.minHeight = `${Math.ceil(lines.length * lineHeight + 12 + above + below)}px`;
}

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
  sampleSettings.set(container, {text, size, coordinates});
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
  fitSample(sample, font, text, size);
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
      const current = sampleSettings.get(container);
      updateSample(container, font, current.text, current.size, current.coordinates);
    } catch (error) {
      if (!container.isConnected) return;
      sample.classList.add('loading');
      status.textContent = error.message;
      status.className = 'render-status error';
    }
  });
}
