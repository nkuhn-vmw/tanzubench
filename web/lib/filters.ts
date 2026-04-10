import type { Enriched } from './enriched';

export type JudgeMode = 'full' | 'core';
export type ViewName = 'composite' | 'ttft' | 'tps' | 'accuracy';

export interface FilterState {
  foundation?: string;
  engine?: string;
  hardware?: 'cpu' | 'gpu';
  search?: string;
  judgeMode: JudgeMode;
  sortBy: ViewName;
}

export const DEFAULT_VIEW: ViewName = 'composite';
export const DEFAULT_JUDGE_MODE: JudgeMode = 'full';

const KNOWN_VIEWS: readonly ViewName[] = ['composite', 'ttft', 'tps', 'accuracy'] as const;

// Backwards compat: the old "speed" view name maps to "ttft" and "value" maps
// to "composite" so any existing shared URLs continue to work.
const VIEW_ALIASES: Record<string, ViewName> = {
  speed: 'ttft',
  value: 'composite',
};

export function parseViewParam(raw: string | null | undefined): ViewName {
  if (!raw) return DEFAULT_VIEW;
  if (raw in VIEW_ALIASES) return VIEW_ALIASES[raw];
  return (KNOWN_VIEWS as readonly string[]).includes(raw) ? (raw as ViewName) : DEFAULT_VIEW;
}

export function parseJudgeModeParam(raw: string | null | undefined): JudgeMode {
  if (raw === 'core') return 'core';
  return DEFAULT_JUDGE_MODE;
}

/**
 * Pure filter: returns a new array containing only Enriched rows that match
 * every provided filter dimension.
 *
 * - judgeMode 'full'  → drop rows where judgeConfigured === false
 * - judgeMode 'core'  → show all rows
 */
export function applyFilters(results: Enriched[], filters: FilterState): Enriched[] {
  return results.filter((r) => {
    const res = r.result;

    if (filters.judgeMode === 'full' && !r.judgeConfigured) return false;
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
