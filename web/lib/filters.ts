import type { Enriched } from './enriched';

export interface FilterState {
  foundation?: string;
  engine?: string;
  hardware?: 'cpu' | 'gpu';
  search?: string;
}

/**
 * Pure filter: returns a new array containing only Enriched rows that match
 * every provided filter dimension.
 *
 * Judge mode is hardcoded to 'full': only rows where judgeConfigured === true
 * are shown.
 */
export function applyFilters(results: Enriched[], filters: FilterState): Enriched[] {
  return results.filter((r) => {
    const res = r.result;

    if (!r.judgeConfigured) return false;
    if (filters.foundation && res.meta.foundation !== filters.foundation) return false;
    if (filters.engine && res.engine.name !== filters.engine) return false;
    if (filters.hardware === 'cpu' && res.hardware.gpu_count > 0) return false;
    if (filters.hardware === 'gpu' && res.hardware.gpu_count === 0) return false;
    if (filters.search) {
      const q = filters.search.toLowerCase();
      if (!r.model.toLowerCase().includes(q)) return false;
    }
    return true;
  });
}
