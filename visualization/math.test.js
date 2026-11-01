'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const M = require('./math.js');
const court = { left: -25, right: 25, baseline: -5.25, half: 41.75, hexRadius: 2,
  view: { left: -27, top: 43.75, width: 54, height: 51 } };
const shot = (x, y, made, value = 2, probability = null) => [x, y, made, 0, 0, 0, 0, 4, 120, value, probability, 'game', 'event'];
test('Wilson intervals include genuine 0%, 100%, and no data separately', () => {
  assert.equal(M.wilson(0, 0), null);
  const zero = M.wilson(0, 10), full = M.wilson(10, 10), half = M.wilson(5, 10);
  assert.ok(zero[0] < 1e-12 && Math.abs(zero[1] - 27.7533) < .001);
  assert.ok(Math.abs(full[0] - 72.2467) < .001 && Math.abs(full[1] - 100) < 1e-10);
  assert.ok(half[0] < 50 && half[1] > 50);
  assert.equal(M.summarize([]).fg, null);
  assert.equal(M.summarize([shot(0, 0, 0)]).fg, 0);
});
test('Expected points is mean(probability × shot value), with explicit coverage', () => {
  const stats = M.summarize([shot(0, 0, 0, 2, 0), shot(1, 0, 1, 3, .5),
    shot(2, 0, 1, 2, 1), shot(3, 0, 0, 3, null)]);
  assert.equal(stats.attempts, 4); assert.equal(stats.made, 2); assert.equal(stats.fg, 50);
  assert.equal(stats.predictions, 3); assert.equal(stats.expectedN, 3);
  assert.equal(stats.probability, .5); assert.equal(stats.expected, 3.5 / 3);
  assert.equal(M.summarize([shot(0, 0, 1)]).expected, null);
});
test('Hexagons conserve mapped attempts and their original locations', () => {
  const rows = [shot(0, 0, 0), shot(-22.5, 1, 1, 3), shot(22.5, 1, 0, 3),
    shot(0, 60, 0, 3), shot(null, 0, 1), shot(0, -5.25, 1), shot(25, 41.75, 0)];
  const before = JSON.stringify(rows), bins = M.aggregate(rows, court);
  assert.equal(Array.from(bins.values()).reduce((n, b) => n + b.stats.attempts, 0), 5);
  assert.equal(Array.from(bins.values()).reduce((n, b) => n + b.stats.made, 0), 2);
  assert.ok(Array.from(bins.values()).some(b => b.stats.attempts === 0 && b.stats.fg === null));
  assert.equal(JSON.stringify(rows), before);
  assert.notEqual(M.hexId(-22.5, 1, 2), M.hexId(22.5, 1, 2));
  for (const b of bins.values()) for (const row of b.rows) {
    const center = M.hexCenter(b.id, 2);
    assert.ok(Math.hypot(row[0] - center[0], row[1] - center[1]) <= 2 + 1e-9);
  }
});
test('Every hex center maps back to its own cell, including negative coordinates', () => {
  for (let q = -20; q <= 20; q++) for (let r = -5; r <= 20; r++) {
    const id = `${q},${r}`, point = M.hexCenter(id, 2);
    assert.equal(M.hexId(...point, 2), id);
    for (const vertex of M.hexVertices(id, 2)) assert.ok(Math.abs(Math.hypot(vertex[0] - point[0], vertex[1] - point[1]) - 2) < 1e-10);
  }
});
test('SVG and canvas use identical undistorted transforms at mobile/tablet/desktop widths', () => {
  for (const width of [280, 390, 640, 760]) {
    for (const point of [[0, 0], [-8, 13.75], [-22, 8.948], [25, 41.75]]) {
      const pixel = M.worldToScreen(...point, width, court), back = M.screenToWorld(...pixel, width, court);
      assert.ok(Math.abs(back[0] - point[0]) < 1e-10 && Math.abs(back[1] - point[1]) < 1e-10);
    }
    const basket = M.worldToScreen(0, 0, width, court);
    const dx = M.worldToScreen(10, 0, width, court), dy = M.worldToScreen(0, 10, width, court);
    assert.ok(Math.abs(dx[0] - basket[0] - (basket[1] - dy[1])) < 1e-10);
  }
});
if (process.env.SHOT_PACKET) test('Actual NBA packet conserves filtered counts in every hexbin', () => {
  const packet = JSON.parse(require('node:fs').readFileSync(process.env.SHOT_PACKET, 'utf8'));
  for (const zone of [null, ...packet.zones.keys()]) {
    const rows = zone === null ? packet.rows : packet.rows.filter(r => r[M.F.zone] === zone);
    const plotted = rows.filter(r => M.visible(r, packet.court));
    const bins = M.aggregate(rows, packet.court), totals = Array.from(bins.values());
    assert.equal(totals.reduce((n, b) => n + b.stats.attempts, 0), plotted.length);
    assert.equal(totals.reduce((n, b) => n + b.stats.made, 0), plotted.filter(r => r[M.F.made] === 1).length);
    assert.equal(totals.reduce((n, b) => n + b.stats.expectedN, 0), 0);
    assert.equal(M.summarize(rows).attempts, rows.length);
  }
});
