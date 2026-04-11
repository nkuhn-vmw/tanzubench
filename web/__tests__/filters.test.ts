import { describe, it, expect } from 'vitest';
import {
  applyFilters,
  type FilterState,
} from '@/lib/filters';
import type { Enriched } from '@/lib/enriched';
import type { Result } from '@/lib/schema';

/** Minimal Enriched factory — only fields used by applyFilters need to be real. */
function mk(overrides: {
  id?: string;
  model?: string;
  foundation?: string;
  engine?: 'ollama' | 'vllm' | 'other';
  hardware?: 'cpu' | 'gpu';
  judgeConfigured?: boolean;
  composite?: number | null;
} = {}): Enriched {
  const gpuCount = overrides.hardware === 'gpu' ? 2 : 0;
  const engine = overrides.engine ?? 'ollama';
  const foundation = overrides.foundation ?? 'dev210';
  const model = overrides.model ?? 'gemma4:e4b';

  // Minimal Result stub — only fields accessed by applyFilters need values
  const result = {
    meta: { foundation, timestamp: '2026-04-06T00:00:00Z' },
    engine: { name: engine, version: null, config: {} },
    hardware: { gpu_count: gpuCount },
    grading: { judge_configured: overrides.judgeConfigured ?? true, skipped_categories: [] },
    summary: {
      composite_score: overrides.composite ?? 1.0,
      composite_max: 1.0,
      composite_over: 1,
      headline_metric: 'composite_score',
      headline_value: 1.0,
      category_scores: [],
    },
    tests: [],
    target: { name: model },
    result_type: 'suite',
    schema_version: '2.0.0',
  } as unknown as Result;

  return {
    id: overrides.id ?? 'x',
    model,
    modelDisplay: model,
    foundation,
    hardware: overrides.hardware ?? 'cpu',
    composite: overrides.composite ?? 1.0,
    compositeOver: 1,
    judgeConfigured: overrides.judgeConfigured ?? true,
    categoryScoresByName: {} as Enriched['categoryScoresByName'],
    result,
    path: 'results/x.json',
  };
}

const FIXTURES: Enriched[] = [
  mk({ id: 'a', model: 'gemma4:e4b',    foundation: 'dev210', engine: 'ollama', hardware: 'cpu' }),
  mk({ id: 'b', model: 'gemma4:26b',    foundation: 'dev210', engine: 'ollama', hardware: 'cpu' }),
  mk({ id: 'c', model: 'ministral-3:3b', foundation: 'cdc',  engine: 'ollama', hardware: 'cpu' }),
  mk({ id: 'd', model: 'llama3.1:8b',   foundation: 'cdc',   engine: 'ollama', hardware: 'cpu' }),
  mk({ id: 'e', model: 'qwen3.5-27b',   foundation: 'tdc',   engine: 'vllm',   hardware: 'gpu' }),
];

const EMPTY_FILTERS: FilterState = {};

describe('applyFilters', () => {
  it('returns all results with empty filters (all judge-configured)', () => {
    expect(applyFilters(FIXTURES, EMPTY_FILTERS)).toEqual(FIXTURES);
  });

  it('drops rows where judgeConfigured === false', () => {
    const withUnjudged = [
      mk({ id: 'j1', model: 'model-a', judgeConfigured: true  }),
      mk({ id: 'j2', model: 'model-b', judgeConfigured: false }),
    ];
    const out = applyFilters(withUnjudged, EMPTY_FILTERS);
    expect(out.map((r) => r.id)).toEqual(['j1']);
  });

  it('filters by foundation', () => {
    const out = applyFilters(FIXTURES, { foundation: 'dev210' });
    expect(out.map((r) => r.id)).toEqual(['a', 'b']);
  });

  it('filters by engine', () => {
    const out = applyFilters(FIXTURES, { engine: 'vllm' });
    expect(out).toHaveLength(1);
    expect(out[0].id).toBe('e');
  });

  it('filters by hardware cpu', () => {
    const out = applyFilters(FIXTURES, { hardware: 'cpu' });
    expect(out.map((r) => r.id)).toEqual(['a', 'b', 'c', 'd']);
  });

  it('filters by hardware gpu', () => {
    const out = applyFilters(FIXTURES, { hardware: 'gpu' });
    expect(out.map((r) => r.id)).toEqual(['e']);
  });

  it('composes multiple filters (intersection)', () => {
    const out = applyFilters(FIXTURES, { foundation: 'dev210', engine: 'ollama' });
    expect(out.map((r) => r.id)).toEqual(['a', 'b']);
  });

  it('case-insensitive search on model name', () => {
    const out = applyFilters(FIXTURES, { search: 'GEMMA4' });
    expect(out.map((r) => r.id)).toEqual(['a', 'b']);
  });

  it('ignores filters with empty string values', () => {
    const out = applyFilters(FIXTURES, { foundation: '', engine: '' });
    expect(out).toEqual(FIXTURES);
  });
});
