// Estimated offscreen rows become measured rows as their real fonts load.
export class PreviewRows {
  reset(ids, estimate) {
    this.ids = ids;
    this.estimate = estimate;
    this.heights = new Map();
    this.rebuild();
  }
  rebuild() {
    this.offsets = [0];
    for (const id of this.ids) this.offsets.push(this.offsets.at(-1) + (this.heights.get(id) ?? this.estimate));
  }
  measure(entries) {
    let changed = false;
    for (const [id, height] of entries) {
      const rounded = Math.ceil(height);
      if (this.heights.get(id) !== rounded) { this.heights.set(id, rounded); changed = true; }
    }
    if (changed) this.rebuild();
    return changed;
  }
  indexAt(y) {
    let low = 0, high = this.ids.length;
    while (low < high) {
      const mid = (low + high) >> 1;
      if (this.offsets[mid + 1] <= y) low = mid + 1;
      else high = mid;
    }
    return Math.min(low, Math.max(0, this.ids.length - 1));
  }
  get total() { return this.offsets.at(-1); }
}
