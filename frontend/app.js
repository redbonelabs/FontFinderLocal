import {createSample, updateSample} from './fonts.js';

const $ = id => document.getElementById(id);
const state = {fonts: [], byId: new Map(), filtered: [], favorites: new Set(), settings: null,
  directories: [], token: '', revision: -1, scan: {}, mode: 'library', nodes: new Map(), detail: null,
  variations: new Map(), canOpenFolder: false};
let saveTimer, toastTimer, pollTimer, scrollFrame;
let saveChain = Promise.resolve();

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function toast(message, error = false) {
  clearTimeout(toastTimer);
  $('toast').textContent = message;
  $('toast').className = error ? 'error' : '';
  $('toast').hidden = false;
  toastTimer = setTimeout(() => { $('toast').hidden = true; }, error ? 7000 : 3000);
}

async function api(path, method = 'GET', body, keepalive = false) {
  const response = await fetch(`/api${path}`, {method, keepalive,
    headers: {'Content-Type': 'application/json', 'X-FontFinder-Token': state.token},
    ...(body === undefined ? {} : {body: JSON.stringify(body)})});
  if (!response.ok) {
    let message = `Local request failed (${response.status}).`;
    try { const result = await response.json(); if (typeof result.detail === 'string') message = result.detail; } catch {}
    throw new Error(message);
  }
  return response.json();
}

function persist() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    const settings = {...state.settings};
    saveChain = saveChain.then(() => api('/settings', 'PUT', settings)).catch(error => toast(`Could not save preferences: ${error.message}`, true));
  }, 300);
}

function resetFilters() {
  Object.assign(state.settings, {query: '', style: 'all', category: 'all', source: 'all', favorites_only: false});
  syncControls(); applyFilters(); persist();
}

function syncControls() {
  const s = state.settings;
  $('preview-text').value = s.text; $('font-size').value = s.size;
  $('size-output').textContent = `${s.size} px`; $('search').value = s.query;
  $('style-filter').value = s.style; $('category-filter').value = s.category;
  $('source-filter').value = s.source; $('sort').value = s.sort;
  $('favorites-only').setAttribute('aria-pressed', s.favorites_only);
  $('favorites-only').textContent = `${s.favorites_only ? '★' : '☆'} Favorites`;
  $('density').setAttribute('aria-pressed', s.density === 'compact');
  const label = `Switch to ${s.density === 'compact' ? 'comfortable' : 'compact'} view`;
  $('density').title = label; $('density').setAttribute('aria-label', label);
  $('library').classList.toggle('compact', s.density === 'compact');
}

function applyFilters(resetScroll = true) {
  const s = state.settings, query = s.query.toLocaleLowerCase().trim();
  state.filtered = state.fonts.filter(f => {
    if (query && !`${f.family} ${f.full_name} ${f.style}`.toLocaleLowerCase().includes(query)) return false;
    if (s.favorites_only && !state.favorites.has(f.id)) return false;
    if (s.category !== 'all' && f.category !== s.category) return false;
    if (s.source !== 'all' && !f.sources.includes(s.source)) return false;
    if (s.style === 'bold' && f.weight < 700) return false;
    if (s.style === 'italic' && !f.italic) return false;
    if (s.style === 'regular' && (f.italic || f.weight < 350 || f.weight > 500)) return false;
    if (s.style === 'variable' && !f.axes.length) return false;
    return true;
  });
  state.filtered.sort((a, b) => {
    if (s.sort === 'favorites') {
      const favorite = Number(state.favorites.has(b.id)) - Number(state.favorites.has(a.id));
      if (favorite) return favorite;
    }
    if (s.sort === 'style') {
      const style = a.style.localeCompare(b.style); if (style) return style;
    }
    return a.family.localeCompare(b.family) || a.weight - b.weight || a.style.localeCompare(b.style) || a.id.localeCompare(b.id);
  });
  $('library-count').textContent = state.fonts.length.toLocaleString();
  $('result-count').textContent = `${state.filtered.length.toLocaleString()} of ${state.fonts.length.toLocaleString()} faces`;
  $('footer-count').textContent = `${new Set(state.fonts.map(f => f.family)).size.toLocaleString()} families · ${state.fonts.length.toLocaleString()} faces`;
  if (resetScroll) $('library').scrollTop = 0;
  clearNodes(); renderWindow(); updateCompareCount();
}

function rowHeight() { return Math.max(state.settings.density === 'compact' ? 116 : 157, state.settings.size * 1.2 + (state.settings.density === 'compact' ? 104 : 131)); }
function clearNodes() { state.nodes.clear(); $('virtual-list').replaceChildren(); }
function renderWindow() {
  if (!state.settings || state.mode !== 'library' || $('browser-view').hidden) return;
  const viewport = $('library'), row = rowHeight();
  $('virtual-list').style.height = `${state.filtered.length * row}px`;
  const start = Math.max(0, Math.floor(viewport.scrollTop / row) - 2);
  const end = Math.min(state.filtered.length, Math.ceil((viewport.scrollTop + viewport.clientHeight) / row) + 2);
  const visible = new Set();
  for (let i = start; i < end; i++) {
    const font = state.filtered[i]; visible.add(font.id);
    let card = state.nodes.get(font.id);
    if (!card) {
      card = createCard(font); state.nodes.set(font.id, card); $('virtual-list').append(card);
    }
    card.style.top = `${i * row}px`; card.style.height = `${row - 12}px`;
  }
  for (const [id, card] of state.nodes) if (!visible.has(id)) { card.remove(); state.nodes.delete(id); }
  const empty = !state.filtered.length;
  $('empty-state').hidden = !empty;
  const loading = state.revision < 0 || (state.scan.running && !state.fonts.length);
  $('empty-title').textContent = loading ? 'Discovering your fonts…' : !state.fonts.length ? 'Your collection starts here' : 'No matching fonts';
  $('empty-message').textContent = loading ? 'Reading local font files. Your library will appear when the scan finishes.' : !state.fonts.length ? 'Add a font folder in Settings, or rescan your installed fonts.' : 'Try a different search or clear your filters.';
  $('clear-filters').hidden = !state.fonts.length;
}

function actionButton(label, text, handler, pressed) {
  const button = element('button', 'icon-button', text);
  button.title = label; button.setAttribute('aria-label', label);
  if (pressed !== undefined) button.setAttribute('aria-pressed', pressed);
  button.addEventListener('click', handler); return button;
}

function createCard(font, comparison = false) {
  const card = element('article', 'font-card');
  const heading = element('div', 'card-heading');
  const title = element('button', 'font-title', font.family);
  title.title = `Details for ${font.full_name}`; title.addEventListener('click', () => showDetails(font));
  heading.append(title, element('span', 'font-style', font.style));
  if (font.axes.length) heading.append(element('span', 'card-badge', 'VARIABLE'));
  else if (font.sources.includes('custom')) heading.append(element('span', 'card-badge', 'CUSTOM'));
  const actions = element('div', 'card-actions');
  const fav = state.favorites.has(font.id), selected = state.settings.compare.includes(font.id);
  const favorite = actionButton(`Favorite ${font.full_name}`, fav ? '★' : '☆', async () => {
    favorite.disabled = true;
    try {
      const result = await api(`/favorites/${font.id}`, 'PUT', {enabled: !state.favorites.has(font.id)});
      state.favorites = new Set(result.favorites); applyFilters(false); renderCompare();
    } catch (error) { toast(error.message, true); } finally { favorite.disabled = false; }
  }, fav);
  actions.append(favorite, actionButton(comparison ? `Remove ${font.full_name} from comparison` : `Compare ${font.full_name}`, comparison ? '×' : selected ? '✓' : '+', () => toggleCompare(font), selected), actionButton(`Details for ${font.full_name}`, 'ⓘ', () => showDetails(font)));
  heading.append(actions); card.append(heading);
  createSample(card, font, state.settings.text, state.settings.size, state.variations.get(font.id));
  if (comparison) card.style.height = `${rowHeight() - 12}px`;
  return card;
}

function toggleCompare(font) {
  const selected = state.settings.compare;
  if (selected.includes(font.id)) state.settings.compare = selected.filter(id => id !== font.id);
  else if (selected.length >= 12) { toast('Select up to 12 fonts for comparison. Remove one to add another.'); return; }
  else state.settings.compare = [...selected, font.id];
  persist(); updateCompareCount(); clearNodes(); renderWindow(); renderCompare();
}
function updateCompareCount() { $('compare-count').textContent = state.settings.compare.filter(id => state.byId.has(id)).length; }
function renderCompare() {
  if (state.mode !== 'compare') { $('compare-list').replaceChildren(); return; }
  const fonts = state.settings.compare.map(id => state.byId.get(id)).filter(Boolean);
  $('compare-list').replaceChildren(...fonts.map(f => createCard(f, true)));
  $('clear-compare').disabled = !state.settings.compare.length;
  if (!fonts.length) {
    const empty = element('div', 'empty-state');
    empty.append(element('span', 'empty-icon', 'Aa / Aa'), element('h2', '', 'A fresh perspective, side by side.'), element('p', '', 'Use the + button on any font in your library to compare it here.'));
    $('compare-list').append(empty);
  }
}

function setMode(mode) {
  state.mode = mode; $('library').hidden = mode !== 'library'; $('comparison').hidden = mode !== 'compare';
  $('tab-library').classList.toggle('active', mode === 'library'); $('tab-compare').classList.toggle('active', mode === 'compare');
  document.querySelector('.filterbar').hidden = mode === 'compare';
  document.querySelector('.view-options').hidden = mode === 'compare';
  if (mode === 'compare') clearNodes();
  renderWindow(); renderCompare();
}

function updatePreviews() {
  $('size-output').textContent = `${state.settings.size} px`;
  for (const container of document.querySelectorAll('[data-font-id]')) {
    const font = state.byId.get(container.dataset.fontId);
    if (font) updateSample(container, font, state.settings.text, state.settings.size, state.variations.get(font.id));
    if (container.classList.contains('font-card')) container.style.height = `${rowHeight() - 12}px`;
  }
  renderWindow(); persist();
}

function showDetails(font) {
  state.detail = font; $('details-title').textContent = font.family;
  $('details-subtitle').textContent = `${font.style} · ${font.format}${font.axes.length ? ' · Variable' : ''}`;
  $('details-preview').replaceChildren();
  createSample($('details-preview'), font, state.settings.text, state.settings.size, state.variations.get(font.id));
  const rows = [['Full name', font.full_name], ['PostScript name', font.postscript_name || 'Not provided'], ['Style', font.style], ['Weight', String(font.weight)], ['Italic / oblique', font.italic ? 'Yes' : 'No'], ['Category', font.category === 'unknown' ? 'Unclassified (not declared)' : font.category], ['Format', `${font.format} · ${font.container}`], ['Face index', String(font.face_index)], ['Unicode coverage', `${font.glyph_count.toLocaleString()} characters`], ['Source', font.sources.join(', ')], ['Source path', font.path]];
  if (font.locations.length > 1) rows.push(['Duplicate locations', font.locations.slice(1).map(l => l.path).join('\n')]);
  $('metadata').replaceChildren(...rows.flatMap(([key, value]) => [element('dt', '', key), element('dd', '', value)]));
  $('open-folder').hidden = !state.canOpenFolder;
  renderVariations(font);
  if (!$('details-dialog').open) $('details-dialog').showModal();
}

function renderVariations(font) {
  const host = $('variation-controls'); host.replaceChildren();
  if (!font.axes.length) return;
  const heading = element('div', 'variation-heading'); heading.append(element('h3', '', 'Variable font axes'));
  const reset = element('button', 'button secondary', 'Reset axes');
  reset.addEventListener('click', () => { state.variations.delete(font.id); renderVariations(font); updatePreviews(); }); heading.append(reset); host.append(heading);
  if (font.instances.length) {
    const select = element('select'); select.setAttribute('aria-label', 'Named font instance');
    const first = element('option', '', 'Choose a named instance'); first.value = ''; select.append(first);
    font.instances.forEach((instance, i) => {
      const option = element('option', '', instance.name || `Instance ${i + 1}`); option.value = i;
      const current = state.variations.get(font.id);
      if (current && Object.entries(instance.coordinates).every(([tag, value]) => current[tag] === value)) option.selected = true;
      select.append(option);
    });
    select.addEventListener('change', () => { if (select.value === '') return; state.variations.set(font.id, {...font.instances[Number(select.value)].coordinates}); renderVariations(font); updatePreviews(); }); host.append(select);
  }
  const coordinates = state.variations.get(font.id) || {};
  for (const axis of font.axes) {
    const row = element('div', 'axis-control'), label = element('label', '', `${axis.name} (${axis.tag})`), output = element('output', '', String(coordinates[axis.tag] ?? axis.default));
    const slider = element('input'); slider.type = 'range'; slider.min = axis.min; slider.max = axis.max;
    slider.step = (axis.max - axis.min) / 1000 || 1; slider.value = coordinates[axis.tag] ?? axis.default;
    slider.id = `axis-${axis.tag}`; label.htmlFor = slider.id; label.append(output);
    slider.addEventListener('input', () => { const value = Number(slider.value); state.variations.set(font.id, {...state.variations.get(font.id), [axis.tag]: value}); output.value = String(Math.round(value * 100) / 100); const instance = host.querySelector('select'); if (instance) instance.value = ''; updatePreviews(); }); row.append(label, slider); host.append(row);
  }
  host.append(element('p', 'subtitle', 'Axis changes apply to previews during this session.'));
}

function renderDirectories() {
  $('directory-list').replaceChildren();
  if (!state.directories.length) { $('directory-list').append(element('p', '', 'No custom folders yet. Your installed Windows fonts are included automatically.')); return; }
  for (const directory of state.directories) {
    const row = element('div', 'directory-row'), info = element('div');
    info.append(element('div', 'path', directory.path), element('small', '', directory.recursive ? 'Includes subfolders' : 'This folder only'));
    const remove = element('button', 'button secondary', 'Remove');
    remove.setAttribute('aria-label', `Remove folder ${directory.path}`);
    remove.addEventListener('click', async () => {
      remove.disabled = true;
      try { const result = await api(`/directories/${directory.id}`, 'DELETE'); state.directories = result.directories; renderDirectories(); await poll(); toast('Folder removed. Original font files are unchanged.'); }
      catch (error) { toast(error.message, true); } finally { remove.disabled = false; }
    }); row.append(info, remove); $('directory-list').append(row);
  }
}

function renderScan() {
  const scan = state.scan, issues = scan.issues || [];
  const message = scan.running ? `Scanning your collection · ${scan.processed} of ${scan.total || '…'} files` : issues.length ? `${issues.length} discovery issue${issues.length === 1 ? '' : 's'} · See Settings for details` : `${scan.processed || 0} files scanned · ${scan.cached || 0} loaded from cache`;
  $('scan-status').hidden = !scan.running && !issues.length;
  $('scan-status').textContent = message; $('settings-scan').textContent = message;
  $('rescan').disabled = !!scan.running; $('settings-rescan').disabled = !!scan.running;
  $('scan-problems').hidden = !issues.length; $('problem-summary').textContent = `Discovery issues (${issues.length})`;
  $('problem-list').replaceChildren(...issues.map(issue => { const row = element('div', 'problem'); row.append(element('strong', '', issue.path), element('span', '', issue.message)); return row; }));
}

async function poll() {
  clearTimeout(pollTimer);
  try {
    const scan = await api('/scan'); state.scan = scan; renderScan();
    if (scan.revision !== state.revision) {
      const catalog = await api('/fonts'); state.revision = catalog.revision; state.fonts = catalog.fonts;
      state.byId = new Map(state.fonts.map(f => [f.id, f])); applyFilters(false); renderCompare();
    }
    renderWindow();
  } catch (error) { $('scan-status').hidden = false; $('scan-status').textContent = `Connection interrupted. ${error.message} Retrying…`; }
  pollTimer = setTimeout(poll, state.scan.running ? 650 : 5000);
}

function showView(settings) {
  $('browser-view').hidden = settings; $('settings-view').hidden = !settings;
  $('nav-browser').classList.toggle('active', !settings); $('nav-settings').classList.toggle('active', settings);
  if (!settings) renderWindow();
}

function wireEvents() {
  $('nav-browser').addEventListener('click', () => showView(false));
  document.querySelector('.brand').addEventListener('click', () => showView(false));
  $('nav-settings').addEventListener('click', () => showView(true));
  $('preview-text').addEventListener('input', event => { state.settings.text = event.target.value; updatePreviews(); });
  $('font-size').addEventListener('input', event => { state.settings.size = Number(event.target.value); updatePreviews(); });
  for (const [id, key] of [['search', 'query'], ['style-filter', 'style'], ['category-filter', 'category'], ['source-filter', 'source'], ['sort', 'sort']]) {
    $(id).addEventListener(id === 'search' ? 'input' : 'change', event => { state.settings[key] = event.target.value; applyFilters(); persist(); });
  }
  $('favorites-only').addEventListener('click', () => { state.settings.favorites_only = !state.settings.favorites_only; syncControls(); applyFilters(); persist(); });
  $('density').addEventListener('click', () => { state.settings.density = state.settings.density === 'compact' ? 'comfortable' : 'compact'; syncControls(); clearNodes(); renderWindow(); persist(); });
  $('clear-filters').addEventListener('click', resetFilters);
  $('tab-library').addEventListener('click', () => setMode('library')); $('tab-compare').addEventListener('click', () => setMode('compare'));
  $('clear-compare').addEventListener('click', () => { state.settings.compare = []; updateCompareCount(); renderCompare(); persist(); });
  $('library').addEventListener('scroll', () => { cancelAnimationFrame(scrollFrame); scrollFrame = requestAnimationFrame(renderWindow); }, {passive: true});
  new ResizeObserver(() => renderWindow()).observe($('library'));
  for (const id of ['rescan', 'settings-rescan']) $(id).addEventListener('click', async () => {
    $(id).disabled = true;
    try { await api('/rescan', 'POST'); await poll(); } catch (error) { toast(error.message, true); $(id).disabled = false; }
  });
  $('close-details').addEventListener('click', () => $('details-dialog').close());
  $('details-dialog').addEventListener('click', event => { if (event.target === $('details-dialog')) { const rect = event.target.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) event.target.close(); } });
  for (const [id, key] of [['copy-name', 'full_name'], ['copy-path', 'path']]) $(id).addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(state.detail[key]); toast(id === 'copy-name' ? 'Font name copied.' : 'Source path copied.'); } catch { toast('Clipboard permission was denied. Select and copy the text in the details panel.', true); }
  });
  $('open-folder').addEventListener('click', async () => { try { await api(`/fonts/${state.detail.id}/open-folder`, 'POST'); } catch (error) { toast(error.message, true); } });
  $('directory-form').addEventListener('submit', async event => {
    event.preventDefault(); const submit = event.target.querySelector('button'); submit.disabled = true; $('directory-error').hidden = true;
    try { const result = await api('/directories', 'POST', {path: $('directory-path').value, recursive: $('recursive').checked}); state.directories = result.directories; $('directory-path').value = ''; renderDirectories(); await poll(); toast('Folder added. Scanning for fonts…'); }
    catch (error) { $('directory-error').textContent = error.message; $('directory-error').hidden = false; } finally { submit.disabled = false; }
  });
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden' && state.settings) { clearTimeout(saveTimer); api('/settings', 'PUT', state.settings, true).catch(() => {}); }
  });
}

async function start() {
  try {
    const boot = await api('/bootstrap'); state.token = boot.token; state.settings = boot.settings;
    state.favorites = new Set(boot.favorites); state.directories = boot.directories; state.canOpenFolder = boot.can_open_folder;
    syncControls(); wireEvents(); renderDirectories(); await poll();
  } catch (error) { toast(`Could not open your library. ${error.message} Reload to retry.`, true); $('result-count').textContent = 'Connection unavailable — reload to retry'; }
}
start();
