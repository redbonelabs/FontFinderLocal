import assert from 'node:assert/strict';
import {PreviewRows} from '../frontend/preview-rows.js';

const rows = new PreviewRows();
rows.reset(['a', 'b', 'c', 'd'], 100);
assert.equal(rows.total, 400);
assert.equal(rows.indexAt(100), 1);
rows.measure([['a', 220.2], ['b', 80], ['d', 900]]);
assert.deepEqual(rows.offsets, [0, 221, 301, 401, 1301]);
assert.equal(rows.indexAt(220), 0);
assert.equal(rows.indexAt(221), 1);
assert.equal(rows.indexAt(1100), 3);
assert.equal(rows.measure([['a', 220.2]]), false);
// Late font loading above the viewport keeps the same row and intra-row offset.
const anchor = rows.indexAt(350), within = 350 - rows.offsets[anchor];
rows.measure([['a', 400]]);
assert.equal(rows.offsets[anchor] + within, 529);
assert.equal(rows.indexAt(529), 2);
// Size/text/density/width invalidation must discard obsolete measurements.
rows.reset(['d', 'a'], 60);
assert.deepEqual(rows.offsets, [0, 60, 120]);
assert.equal(rows.indexAt(999), 1);
rows.reset([], 60);
assert.equal(rows.total, 0);
assert.equal(rows.indexAt(0), 0);
console.log('Preview row measurements, anchors, invalidation and bounds passed.');
