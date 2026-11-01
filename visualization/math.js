/* Pure calculations, also exercised with Node's built-in test runner. */
(function (root) {
  'use strict';
  const F = { x: 0, y: 1, made: 2, player: 3, zone: 4, type: 5, distance: 6,
    period: 7, seconds: 8, value: 9, probability: 10, game: 11, event: 12 };
  const finite = value => typeof value === 'number' && Number.isFinite(value);
  function visible(row, court) {
    return finite(row[F.x]) && finite(row[F.y]) && row[F.x] >= court.left &&
      row[F.x] <= court.right && row[F.y] >= court.baseline && row[F.y] <= court.half;
  }
  function wilson(made, attempts) {
    if (!attempts) return null;
    const z = 1.959963984540054, p = made / attempts, den = 1 + z * z / attempts;
    const center = (p + z * z / (2 * attempts)) / den;
    const half = z * Math.sqrt(p * (1 - p) / attempts + z * z / (4 * attempts ** 2)) / den;
    return [Math.max(0, center - half) * 100, Math.min(1, center + half) * 100];
  }
  function summarize(rows) {
    let made = 0, probabilitySum = 0, predictions = 0, expectedSum = 0, expectedN = 0;
    for (const row of rows) {
      made += row[F.made];
      const p = row[F.probability];
      if (finite(p) && p >= 0 && p <= 1) {
        predictions++; probabilitySum += p;
        if ([2, 3].includes(row[F.value])) { expectedN++; expectedSum += p * row[F.value]; }
      }
    }
    return { attempts: rows.length, made, fg: rows.length ? 100 * made / rows.length : null,
      ci: wilson(made, rows.length), probability: predictions ? probabilitySum / predictions : null,
      predictions, expected: expectedN ? expectedSum / expectedN : null, expectedN };
  }
  // Pointy-top axial lattice, anchored at the basket for every sidebar filter.
  function hexId(x, y, radius) {
    const q = (Math.sqrt(3) / 3 * x - y / 3) / radius, r = (2 / 3 * y) / radius;
    let rx = Math.round(q), rz = Math.round(r), ry = Math.round(-q - r);
    const dx = Math.abs(rx - q), dy = Math.abs(ry + q + r), dz = Math.abs(rz - r);
    if (dx > dy && dx > dz) rx = -ry - rz;
    else if (dy > dz) ry = -rx - rz;
    else rz = -rx - ry;
    return `${rx === 0 ? 0 : rx},${rz === 0 ? 0 : rz}`;
  }
  function hexCenter(id, radius) {
    const [q, r] = id.split(',').map(Number);
    return [radius * Math.sqrt(3) * (q + r / 2), radius * 1.5 * r];
  }
  function hexVertices(id, radius) {
    const [x, y] = hexCenter(id, radius);
    return Array.from({ length: 6 }, (_, i) => {
      const angle = (60 * i - 30) * Math.PI / 180;
      return [x + radius * Math.cos(angle), y + radius * Math.sin(angle)];
    });
  }
  function aggregate(rows, court) {
    const bins = new Map();
    for (let r = -3; r <= 17; r++) for (let q = -19; q <= 12; q++) {
      const id = `${q},${r}`, [x, y] = hexCenter(id, court.hexRadius);
      if (x >= court.left - 2 * court.hexRadius && x <= court.right + 2 * court.hexRadius &&
          y >= court.baseline - 2 * court.hexRadius && y <= court.half + 2 * court.hexRadius)
        bins.set(id, { id, rows: [] });
    }
    for (const row of rows) if (visible(row, court)) {
      const id = hexId(row[F.x], row[F.y], court.hexRadius);
      if (!bins.has(id)) bins.set(id, { id, rows: [] });
      bins.get(id).rows.push(row);
    }
    for (const bin of bins.values()) bin.stats = summarize(bin.rows);
    return bins;
  }
  function worldToScreen(x, y, width, court) {
    return [(x - court.view.left) * width / court.view.width,
      (court.view.top - y) * width / court.view.width];
  }
  function screenToWorld(x, y, width, court) {
    return [x * court.view.width / width + court.view.left,
      court.view.top - y * court.view.width / width];
  }
  const api = { F, finite, visible, wilson, summarize, hexId, hexCenter, hexVertices, aggregate,
    worldToScreen, screenToWorld };
  if (typeof module !== 'undefined') module.exports = api;
  else root.CourtMath = api;
})(typeof window === 'undefined' ? globalThis : window);
