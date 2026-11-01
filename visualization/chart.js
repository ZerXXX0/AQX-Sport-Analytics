/* Local Streamlit component. No remote scripts, model calls, or sampled data. */
'use strict';
const M = window.CourtMath, F = M.F;
const $ = id => document.getElementById(id);
const NS = 'http://www.w3.org/2000/svg';
const number = value => value.toLocaleString('en-US');
const rate = value => M.finite(value) ? `${value.toFixed(1)}%` : 'Unavailable';
const decimal = value => M.finite(value) ? value.toFixed(2) : 'Unavailable';
let packet, rows = [], mapped = [], bins = new Map(), spatial = new Map();
let mode = 'scatter', metric = 'attempts', zone = 'all', threshold = 30;
let selectedHex = null, selectedShot = null, hoveredShot = null, focusedIndex = -1;
let hoveredHex = null, resizeFrame = null, lastRenderKey = null;

function svgNode(tag, attributes = {}) {
  const element = document.createElementNS(NS, tag);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, String(value));
  return element;
}
function post(type, values = {}) {
  window.parent.postMessage({ isStreamlitMessage: true, type, ...values }, '*');
}
function frameHeight() {
  if (resizeFrame) cancelAnimationFrame(resizeFrame);
  resizeFrame = requestAnimationFrame(() => {
    post('streamlit:setFrameHeight', { height: Math.ceil($('explorer').getBoundingClientRect().height) + 6 });
  });
}
function announce(message) { $('live').textContent = message; }
function hideTooltip() { $('tooltip').hidden = true; }
function detailLine(label, value) {
  const line = document.createElement('div'); line.className = 'detail-line';
  const key = document.createElement('span'), content = document.createElement('span');
  key.textContent = label; content.textContent = value;
  line.append(key, content); return line;
}
function fillDetails(element, title, pairs, note) {
  element.replaceChildren();
  const heading = document.createElement('h4'); heading.textContent = title; element.append(heading);
  for (const [label, value] of pairs) element.append(detailLine(label, value));
  if (note) { const p = document.createElement('p'); p.className = 'tip-note'; p.textContent = note; element.append(p); }
}
function showTooltip(title, pairs, note, clientX, clientY) {
  const tooltip = $('tooltip'); fillDetails(tooltip, title, pairs, note); tooltip.hidden = false;
  // The iframe grows with content. Constrain to its *visible* portion inside the
  // parent viewport as well as its own viewport, without accessing parent DOM.
  let top = 8, bottom = window.innerHeight - 8;
  if (visibleViewport) { top = visibleViewport.top + 8; bottom = visibleViewport.bottom - 8; }
  tooltip.style.maxHeight = `${Math.max(80, bottom - top)}px`;
  const bounds = tooltip.getBoundingClientRect();
  const left = Math.max(8, Math.min(clientX + 14, window.innerWidth - bounds.width - 8));
  const desiredY = clientY + 14 + bounds.height < bottom ? clientY + 14 : clientY - bounds.height - 14;
  tooltip.style.left = `${left}px`;
  tooltip.style.top = `${Math.max(top, Math.min(desiredY, bottom - bounds.height))}px`;
}
// IntersectionObserver reports the actual iframe viewport intersection. This
// keeps a hover card in the visible portion when the parent page is scrolled.
let visibleViewport = null;
if ('IntersectionObserver' in window) {
  new IntersectionObserver(entries => {
    const entry = entries[0];
    if (entry && entry.isIntersecting) {
      visibleViewport = { top: entry.intersectionRect.top, bottom: entry.intersectionRect.bottom };
    }
  }, { threshold: Array.from({ length: 21 }, (_, i) => i / 20) }).observe(document.documentElement);
}

function shotPairs(row) {
  const seconds = row[F.seconds], period = row[F.period];
  const clock = M.finite(seconds) ? `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}` : 'Unavailable';
  const p = row[F.probability];
  return [
    ['Result', row[F.made] ? 'Made · circle' : 'Missed · cross'],
    ['Zone', packet.zones[row[F.zone]]], ['Shot type', packet.types[row[F.type]]],
    ['Distance', M.finite(row[F.distance]) ? `${row[F.distance].toFixed(0)} ft` : 'Unavailable'],
    ['Period · time left', `${M.finite(period) ? (period > 4 ? `OT${period - 4}` : `Q${period}`) : 'Unavailable'} · ${clock}`],
    ['Make probability', M.finite(p) ? rate(p * 100) : 'Unavailable'],
    ['Expected points', M.finite(p) && [2, 3].includes(row[F.value]) ? `${decimal(p * row[F.value])} pts/attempt` : 'Unavailable'],
    ['Position', `${row[F.x].toFixed(1)}, ${row[F.y].toFixed(1)} ft`],
    ['Game · event', `${row[F.game] || 'Unavailable'} · ${row[F.event] || 'Unavailable'}`],
  ];
}
function statsPairs(stats) {
  return [['Attempts · made', `${number(stats.attempts)} · ${number(stats.made)}`],
    ['FG%', rate(stats.fg)],
    ['95% Wilson CI · FG%', stats.ci ? `${rate(stats.ci[0])} – ${rate(stats.ci[1])}` : 'No attempts'],
    ['Mean make probability', M.finite(stats.probability) ? rate(stats.probability * 100) : 'Unavailable'],
    ['Mean expected points', M.finite(stats.expected) ? `${decimal(stats.expected)} pts/attempt` : 'Unavailable'],
    ['Prediction coverage', `${number(stats.expectedN)} of ${number(stats.attempts)} attempts`]];
}
function sampleNote(stats) {
  if (!stats.attempts) return 'No data in this area; this is not 0% FG.';
  const count = mode === 'expected' ? stats.expectedN : stats.attempts;
  return count < threshold ? `Insufficient sample · sampel belum mencukupi (n=${number(count)} < ${threshold}).` : `n=${number(count)} ≥ ${threshold}. Descriptive evidence, not a tactical recommendation.`;
}

function drawCourt() {
  const c = packet.court, join = Math.sqrt(c.threeRadius ** 2 - c.cornerX ** 2);
  const arc = (cx, cy, r, start, end) => {
    const points = Array.from({ length: 100 }, (_, i) => {
      const angle = start + (end - start) * i / 99;
      return `${i ? 'L' : 'M'}${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`;
    });
    return points.join(' ');
  };
  const theta = Math.acos(c.cornerX / c.threeRadius);
  const paths = [
    `M${c.left},${c.baseline}H${c.right}V${c.half}H${c.left}Z`,
    `M${-c.keyX},${c.baseline}V${c.freeThrowY}H${c.keyX}V${c.baseline}`,
    `M-6,${c.baseline}V${c.freeThrowY}M6,${c.baseline}V${c.freeThrowY}`,
    arc(0, c.freeThrowY, c.freeThrowRadius, 0, Math.PI),
    arc(0, c.half, 6, Math.PI, 2 * Math.PI),
    `M${-c.cornerX},${c.baseline}V${join}M${c.cornerX},${c.baseline}V${join}`,
    arc(0, 0, c.threeRadius, theta, Math.PI - theta),
    `${arc(0, 0, c.restrictedRadius, 0, Math.PI)}V${c.backboardY}M${c.restrictedRadius},0V${c.backboardY}`,
    `M-3,${c.backboardY}H3`,
    'M-25,22.75H-22M25,22.75H22',
  ];
  const layer = $('court-lines'); layer.replaceChildren();
  for (const d of paths) layer.append(svgNode('path', { d, class: 'halo' }));
  for (const d of paths) layer.append(svgNode('path', { d }));
  layer.append(svgNode('path', { d: arc(0, c.freeThrowY, c.freeThrowRadius, Math.PI, 2 * Math.PI), 'stroke-dasharray': '.45 .35' }));
  layer.append(svgNode('circle', { cx: 0, cy: 0, r: c.rimRadius, class: 'halo' }));
  layer.append(svgNode('circle', { cx: 0, cy: 0, r: c.rimRadius, class: 'rim' }));
}
function hexPoints(id) { return M.hexVertices(id, packet.court.hexRadius).map(p => p.join(',')).join(' '); }
function activeMetric() { return mode === 'expected' ? 'expected' : metric; }
function maxMetric() { return activeMetric() === 'fg' ? 100 : activeMetric() === 'expected' ? 3 : Math.max(1, ...Array.from(bins.values(), b => b.stats.attempts)); }
function color(value, max) {
  const stops = [[38, 53, 99], [54, 138, 175], [118, 213, 213], [243, 206, 117]];
  const t = Math.max(0, Math.min(1, value / max)) * (stops.length - 1);
  const i = Math.min(stops.length - 2, Math.floor(t)), mix = t - i;
  return `rgb(${stops[i].map((v, j) => Math.round(v + mix * (stops[i + 1][j] - v))).join(',')})`;
}
function drawHexes() {
  const layer = $('hexes'); layer.replaceChildren();
  if (mode === 'scatter') return;
  const maximum = maxMetric(), active = activeMetric();
  const sorted = Array.from(bins.values()).sort((a, b) => {
    const ac = M.hexCenter(a.id, packet.court.hexRadius), bc = M.hexCenter(b.id, packet.court.hexRadius);
    return bc[1] - ac[1] || ac[0] - bc[0];
  });
  for (const bin of sorted) {
    const s = bin.stats, value = s[active], count = active === 'expected' ? s.expectedN : s.attempts;
    const noData = !s.attempts || !M.finite(value), low = !noData && count < threshold;
    const polygon = svgNode('polygon', { points: hexPoints(bin.id),
      fill: noData ? 'url(#no-data)' : color(value, maximum), 'fill-opacity': low ? .36 : .9,
      class: `hex${selectedHex === bin.id ? ' selected' : ''}`, 'data-cell': bin.id, 'data-attempts': s.attempts,
      tabindex: s.attempts ? (bin.id === selectedHex ? 0 : -1) : -1,
      role: 'button', 'aria-pressed': selectedHex === bin.id, 'aria-describedby': 'tooltip',
      'aria-label': `Area ${bin.id}. ${s.attempts} attempts, ${s.made} made. FG ${rate(s.fg)}. ${sampleNote(s)}` });
    polygon.addEventListener('pointermove', event => {
      hoveredHex = bin.id; highlight();
      showTooltip(`Area ${bin.id}`, statsPairs(s), sampleNote(s), event.clientX, event.clientY);
    });
    polygon.addEventListener('pointerleave', () => { hoveredHex = null; hideTooltip(); highlight(); });
    polygon.addEventListener('click', event => {
      selectedHex = bin.id; selectedShot = null; hoveredHex = null; hideTooltip();
      updateSelection(); highlight(); updateHexSelection();
      if (event.pointerType === 'touch') announce(`Selected area ${bin.id}. ${s.attempts} attempts.`);
    });
    polygon.addEventListener('focus', () => {
      hoveredHex = bin.id; highlight();
      const rect = polygon.getBoundingClientRect();
      showTooltip(`Area ${bin.id}`, statsPairs(s), sampleNote(s), rect.left, rect.top);
    });
    polygon.addEventListener('blur', () => { hoveredHex = null; hideTooltip(); highlight(); });
    polygon.addEventListener('keydown', event => handleHexKey(event, bin));
    layer.append(polygon);
    if (low) layer.append(svgNode('polygon', { points: hexPoints(bin.id), fill: 'url(#low-sample)', 'pointer-events': 'none' }));
  }
  // One tab stop for the grid; arrow keys reach the other occupied cells.
  if (!layer.querySelector('[tabindex="0"]')) {
    const first = layer.querySelector('.hex[aria-label]:not([aria-label*=" 0 attempts"])');
    if (first) first.setAttribute('tabindex', '0');
  }
}
function updateHexSelection() {
  for (const element of $('hexes').querySelectorAll('.hex')) {
    const selected = element.dataset.cell === selectedHex;
    element.classList.toggle('selected', selected); element.setAttribute('aria-pressed', String(selected));
  }
}
function handleHexKey(event, bin) {
  if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); clearSelection(); return; }
  if (['Enter', ' '].includes(event.key)) { event.preventDefault(); selectedHex = bin.id; selectedShot = null; updateSelection(); highlight(); updateHexSelection(); return; }
  const directions = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, 1], ArrowDown: [0, -1] };
  const direction = directions[event.key]; if (!direction) return;
  event.preventDefault(); const origin = M.hexCenter(bin.id, packet.court.hexRadius);
  let target = null, score = Infinity;
  for (const other of bins.values()) if (other.stats.attempts && other.id !== bin.id) {
    const p = M.hexCenter(other.id, packet.court.hexRadius), dx = p[0] - origin[0], dy = p[1] - origin[1];
    const forward = dx * direction[0] + dy * direction[1];
    if (forward <= 0) continue;
    const candidate = Math.hypot(dx, dy) + 3 * Math.abs(dx * direction[1] - dy * direction[0]);
    if (candidate < score) { target = other.id; score = candidate; }
  }
  if (target) {
    const element = Array.from($('hexes').querySelectorAll('.hex')).find(e => e.dataset.cell === target);
    if (element) { $('hexes').querySelectorAll('[tabindex="0"]').forEach(e => e.setAttribute('tabindex', '-1')); element.setAttribute('tabindex', '0'); element.focus({ preventScroll: true }); }
  }
}
function drawScatter() {
  const canvas = $('shots'), width = $('court-wrap').clientWidth;
  if (!width || !packet) return;
  const height = width * packet.court.view.height / packet.court.view.width;
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio);
  const ctx = canvas.getContext('2d'); ctx.scale(ratio, ratio); ctx.clearRect(0, 0, width, height);
  if (mode !== 'scatter') return;
  const radius = Math.max(1.3, Math.min(2.8, width / 230));
  const alpha = mapped.length > 30000 ? .2 : mapped.length > 3000 ? .38 : .72;
  // All records are rendered; count-dependent opacity replaces random sampling.
  for (const made of [0, 1]) {
    ctx.strokeStyle = '#ffb36e'; ctx.fillStyle = '#66d0ec'; ctx.lineWidth = 1.15;
    ctx.globalAlpha = alpha;
    for (const row of mapped) if (row[F.made] === made) {
      const [x, y] = M.worldToScreen(row[F.x], row[F.y], width, packet.court);
      const outsideSelection = selectedHex && M.hexId(row[F.x], row[F.y], packet.court.hexRadius) !== selectedHex;
      ctx.globalAlpha = outsideSelection ? alpha * .12 : alpha;
      ctx.beginPath();
      if (made) { ctx.arc(x, y, radius, 0, Math.PI * 2); ctx.fill(); }
      else { ctx.moveTo(x - radius, y - radius); ctx.lineTo(x + radius, y + radius); ctx.moveTo(x - radius, y + radius); ctx.lineTo(x + radius, y - radius); ctx.stroke(); }
    }
  }
  ctx.globalAlpha = 1;
}
function highlight() {
  const layer = $('highlight'); layer.replaceChildren();
  const id = hoveredHex || selectedHex;
  if (id) layer.append(svgNode('polygon', { points: hexPoints(id), class: 'hex-hover', 'clip-path': 'url(#bounds)' }));
  for (const row of [selectedShot, hoveredShot]) if (row) {
    const width = $('court-wrap').clientWidth || 600;
    layer.append(svgNode('circle', { cx: row[F.x], cy: row[F.y], r: 7 * packet.court.view.width / width }));
  }
}
function drawLegend() {
  const legend = $('legend'); legend.replaceChildren();
  if (mode === 'scatter') {
    for (const [label, className, symbol] of [['Made', 'made-key', ''], ['Missed', 'missed-key', '×']]) {
      const item = document.createElement('span'); item.className = 'legend-item';
      const icon = document.createElement('span'); icon.className = className; icon.textContent = symbol;
      item.append(icon, document.createTextNode(label)); legend.append(item);
    }
    legend.append(document.createTextNode('All mapped attempts · no sampling')); return;
  }
  const active = activeMetric(), max = maxMetric(), scale = document.createElement('div'); scale.className = 'scale';
  const label = document.createElement('div'); label.textContent = active === 'expected' ? 'Mean expected points / attempt' : active === 'fg' ? 'Field-goal percentage' : 'Attempts per hexbin';
  const bar = document.createElement('div'); bar.className = 'scale-bar';
  const ticks = document.createElement('div'); ticks.className = 'scale-labels';
  for (const value of [0, max / 2, max]) {
    const tick = document.createElement('span'); tick.textContent = active === 'fg' ? `${value.toFixed(0)}%` : active === 'expected' ? `${value.toFixed(1)} pts` : number(Math.round(value)); ticks.append(tick);
  }
  scale.append(label, bar, ticks); legend.append(scale);
  for (const [className, text] of [['no-data-key', 'No data'], ['low-key', `n < ${threshold}`]]) {
    const item = document.createElement('span'); item.className = 'legend-item';
    const swatch = document.createElement('span'); swatch.className = `swatch ${className}`;
    item.append(swatch, document.createTextNode(text)); legend.append(item);
  }
}
function updateSelection() {
  const cell = selectedHex && bins.get(selectedHex);
  const scopeRows = cell ? cell.rows : rows, stats = cell ? cell.stats : M.summarize(scopeRows);
  $('selection-title').textContent = cell ? `Area ${selectedHex}` : zone === 'all' ? 'All zones' : packet.zones[Number(zone)];
  $('selection-subtitle').textContent = cell ? 'Selected hexbin · mapped attempts only' : 'Current filters · all eligible attempts';
  $('clear').disabled = !selectedHex && !selectedShot && zone === 'all';
  const container = $('stats'); container.replaceChildren();
  const entries = [['Attempts', number(stats.attempts), `${number(stats.made)} made`],
    ['FG%', rate(stats.fg), stats.ci ? `95% CI ${rate(stats.ci[0])} – ${rate(stats.ci[1])}` : 'No attempts'],
    ['Expected pts / attempt', decimal(stats.expected), `${number(stats.expectedN)} valid predictions`],
    ['Mean make probability', M.finite(stats.probability) ? rate(stats.probability * 100) : 'Unavailable', 'Model estimate']];
  for (const [label, value, sub] of entries) {
    const stat = document.createElement('div');
    for (const [className, text] of [['stat-label', label], ['stat-value', value], ['stat-sub', sub]]) {
      const part = document.createElement('div'); part.className = className; part.textContent = text; stat.append(part);
    }
    container.append(stat);
  }
  $('sample-status').textContent = sampleNote(stats);
  $('shot-detail').hidden = !selectedShot;
  if (selectedShot) fillDetails($('shot-detail'), packet.players[selectedShot[F.player]], shotPairs(selectedShot), 'Selected shot');
  const invalid = rows.filter(r => !M.finite(r[F.x]) || !M.finite(r[F.y])).length;
  const off = rows.length - mapped.length - invalid;
  $('coverage').textContent = `${number(mapped.length)} of ${number(rows.length)} attempts mapped. ${number(off)} outside the half court; ${number(invalid)} with invalid coordinates. These attempts remain in source-zone totals; positions are never clamped.`;
  $('scope').textContent = `${zone === 'all' ? 'All zones' : packet.zones[Number(zone)]} · ${number(mapped.length)} mapped`;
  const unavailable = mode === 'expected' && !mapped.some(row => M.finite(row[F.probability]) && [2, 3].includes(row[F.value]));
  $('court-empty').hidden = mapped.length > 0 && !unavailable;
  $('court-empty').textContent = unavailable ? 'Expected points unavailable for this selection.' : 'No mapped shots match this selection.';
  const status = $('prediction-status'); status.hidden = mode !== 'expected';
  status.textContent = unavailable ? `Expected points unavailable. ${packet.meta.predictionStatus} No substitute values are generated.` : `Mean expected points uses probability × shot value for each attempt with valid predictions. ${number(stats.expectedN)} of ${number(stats.attempts)} attempts have coverage. This is not observed FG% or actual points.`;
  const m = packet.meta;
  $('data-notes').textContent = `${m.coordinateSource}; units: feet. X increases from the left corner toward the right corner; Y increases toward midcourt. ${m.predictionStatus} ${number(m.invalidPredictions)} invalid predictions excluded from model overlays. ${number(m.invalidResults)} invalid shot results excluded from chart statistics. ${number(m.coordinateMismatches)} derived-coordinate mismatches; original LOC coordinates take precedence.`;
  announce(`${$('selection-title').textContent}. ${stats.attempts} attempts, ${stats.made} made. FG ${rate(stats.fg)}.`);
  frameHeight();
}
function buildZoneList() {
  const list = $('zone-list'); list.replaceChildren();
  packet.zones.forEach((name, index) => {
    const stats = M.summarize(packet.rows.filter(row => row[F.zone] === index));
    const button = document.createElement('button'); button.type = 'button'; button.className = 'zone-card';
    button.setAttribute('aria-pressed', String(zone === String(index)));
    button.append(document.createTextNode(name));
    const summary = document.createElement('span'); summary.textContent = `${number(stats.attempts)} attempts · ${number(stats.made)} made · ${rate(stats.fg)} FG`;
    const interval = document.createElement('span'); interval.textContent = stats.ci ? `95% Wilson CI ${rate(stats.ci[0])} – ${rate(stats.ci[1])}` : 'No attempts';
    if (stats.attempts < threshold) interval.textContent += ' · sampel belum mencukupi';
    button.append(summary, interval);
    const benchmark = packet.benchmarks?.[name];
    if (benchmark) {
      const baseline = document.createElement('span');
      baseline.textContent = `League FG ${rate(benchmark.fg)} · ${number(benchmark.attempts)} attempts`;
      button.append(baseline);
    }
    button.addEventListener('click', () => {
      zone = String(index); $('zone').value = zone; selectedHex = null; selectedShot = null; filterRows();
    }); list.append(button);
  });
}
function filterRows() {
  rows = zone === 'all' ? packet.rows : packet.rows.filter(row => row[F.zone] === Number(zone));
  mapped = rows.filter(row => M.visible(row, packet.court));
  bins = M.aggregate(rows, packet.court); spatial = new Map(); focusedIndex = -1;
  for (const row of mapped) {
    const id = `${Math.floor(row[F.x])},${Math.floor(row[F.y])}`;
    if (!spatial.has(id)) spatial.set(id, []); spatial.get(id).push(row);
  }
  if (selectedHex && !bins.get(selectedHex)?.stats.attempts) selectedHex = null;
  hoveredHex = null; hoveredShot = null; hideTooltip();
  render(); buildZoneList();
}
function render() {
  $('shot-surface').style.pointerEvents = mode === 'scatter' ? 'all' : 'none';
  $('shot-surface').setAttribute('tabindex', mode === 'scatter' ? '0' : '-1');
  $('metric').disabled = mode !== 'heatmap';
  drawHexes(); drawScatter(); drawLegend(); updateSelection(); highlight();
}
function clearSelection() {
  selectedHex = null; selectedShot = null; hoveredShot = null; hoveredHex = null; focusedIndex = -1;
  zone = 'all'; $('zone').value = zone; filterRows();
}
function findShot(event) {
  const rect = $('court-wrap').getBoundingClientRect(), width = rect.width;
  const [x, y] = M.screenToWorld(event.clientX - rect.left, event.clientY - rect.top, width, packet.court);
  const tolerance = 11 * packet.court.view.width / width;
  let nearest = null, distance = tolerance ** 2;
  for (let dx = -Math.ceil(tolerance); dx <= Math.ceil(tolerance); dx++) for (let dy = -Math.ceil(tolerance); dy <= Math.ceil(tolerance); dy++) {
    const bucket = spatial.get(`${Math.floor(x) + dx},${Math.floor(y) + dy}`) || [];
    for (const row of bucket) {
      const d = (row[F.x] - x) ** 2 + (row[F.y] - y) ** 2;
      if (d < distance) { nearest = row; distance = d; }
    }
  }
  return nearest;
}
$('shot-surface').addEventListener('pointermove', event => {
  if (mode !== 'scatter' || event.pointerType === 'touch') return;
  hoveredShot = findShot(event); highlight();
  if (hoveredShot) showTooltip(packet.players[hoveredShot[F.player]], shotPairs(hoveredShot), 'Click to pin this shot.', event.clientX, event.clientY);
  else hideTooltip();
});
$('shot-surface').addEventListener('pointerleave', () => { hoveredShot = null; hideTooltip(); highlight(); });
$('shot-surface').addEventListener('click', event => {
  selectedShot = findShot(event); hoveredShot = null; hideTooltip();
  if (selectedShot) selectedHex = M.hexId(selectedShot[F.x], selectedShot[F.y], packet.court.hexRadius);
  else selectedHex = null;
  updateSelection(); drawScatter(); highlight();
});
$('shot-surface').addEventListener('focus', () => {
  if (!mapped.length || mode !== 'scatter') return;
  focusedIndex = Math.max(0, focusedIndex); hoveredShot = mapped[focusedIndex]; keyboardShot();
});
$('shot-surface').addEventListener('blur', () => { hoveredShot = null; hideTooltip(); highlight(); });
function keyboardShot() {
  const row = hoveredShot; if (!row) return;
  highlight();
  const bounds = $('court-wrap').getBoundingClientRect();
  const [x, y] = M.worldToScreen(row[F.x], row[F.y], bounds.width, packet.court);
  showTooltip(packet.players[row[F.player]], shotPairs(row), 'Enter pins this shot.', bounds.left + x, bounds.top + y);
  announce(`${packet.players[row[F.player]]}, ${row[F.made] ? 'made' : 'missed'}, ${packet.zones[row[F.zone]]}. Shot ${focusedIndex + 1} of ${mapped.length}.`);
}
$('shot-surface').addEventListener('keydown', event => {
  if (!mapped.length) return;
  if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); clearSelection(); return; }
  if (['Enter', ' '].includes(event.key)) {
    event.preventDefault(); selectedShot = hoveredShot || mapped[0];
    selectedHex = M.hexId(selectedShot[F.x], selectedShot[F.y], packet.court.hexRadius);
    updateSelection(); drawScatter(); highlight(); return;
  }
  const delta = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[event.key];
  if (delta !== undefined || ['Home', 'End'].includes(event.key)) {
    event.preventDefault();
    focusedIndex = event.key === 'Home' ? 0 : event.key === 'End' ? mapped.length - 1 : (Math.max(focusedIndex, 0) + delta + mapped.length) % mapped.length;
    hoveredShot = mapped[focusedIndex]; keyboardShot();
  }
});
document.querySelectorAll('[name="mode"]').forEach(input => input.addEventListener('change', () => {
  mode = input.value; hoveredShot = null; hoveredHex = null; hideTooltip(); render();
}));
$('metric').addEventListener('change', event => { metric = event.target.value; hideTooltip(); render(); });
$('zone').addEventListener('change', event => { zone = event.target.value; selectedHex = null; selectedShot = null; filterRows(); });
$('threshold').addEventListener('input', event => {
  threshold = Number(event.target.value); $('threshold-value').value = String(threshold);
  hideTooltip(); drawHexes(); drawLegend(); updateSelection(); buildZoneList();
});
$('clear').addEventListener('click', clearSelection);
document.querySelectorAll('details').forEach(details => details.addEventListener('toggle', frameHeight));
document.addEventListener('keydown', event => { if (event.key === 'Escape') { hideTooltip(); clearSelection(); } });
new ResizeObserver(() => { if (packet) { drawScatter(); highlight(); hideTooltip(); } frameHeight(); }).observe($('court-wrap'));
new ResizeObserver(frameHeight).observe($('explorer'));
window.addEventListener('message', event => {
  if (event.source !== window.parent || event.data?.type !== 'streamlit:render') return;
  try {
    const next = event.data.args.packet;
    if (!next || !Array.isArray(next.rows) || !next.court) throw new Error('Shot data could not be read.');
    // Render messages also arrive on ordinary Streamlit reruns. Reset stale
    // selections for new filter data, preserve them for the identical packet.
    const renderKey = next.revision;
    const changed = renderKey !== lastRenderKey;
    packet = next; lastRenderKey = renderKey;
    if (changed) {
      selectedHex = null; selectedShot = null; zone = 'all';
      const select = $('zone'); select.replaceChildren();
      const all = document.createElement('option'); all.value = 'all'; all.textContent = 'All zones'; select.append(all);
      packet.zones.forEach((label, i) => { const option = document.createElement('option'); option.value = String(i); option.textContent = label; select.append(option); });
    }
    $('loading').hidden = true; $('error').hidden = true; $('content').hidden = false;
    $('explorer').setAttribute('aria-busy', 'false');
    drawCourt(); filterRows(); frameHeight();
  } catch (error) {
    $('loading').hidden = true; $('content').hidden = true; $('error').hidden = false;
    $('error').textContent = `Shot visualization unavailable: ${error.message}`;
    $('explorer').setAttribute('aria-busy', 'false'); frameHeight();
  }
});
post('streamlit:componentReady', { apiVersion: 1 }); frameHeight();
