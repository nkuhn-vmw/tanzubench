import { describe, it, expect } from 'vitest';
import {
  applyFilters,
  parseViewParam,
  parseJudgeModeParam,
  DEFAULT_VIEW,
  DEFAULT_JUDGE_MODE,
  type FilterState,
  type ViewName,
  type JudgeMode,
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

const FULL_STATE: FilterState = { judgeMode: 'full', sortBy: 'composite' };

describe('applyFilters', () => {
  it('returns all results with empty filter (judgeMode full, all judge-configured)', () => {
    expect(applyFilters(FIXTURES, FULL_STATE)).toEqual(FIXTURES);
  });

  it('filters by foundation', () => {
    const out = applyFilters(FIXTURES, { ...FULL_STATE, foundation: 'dev210' });
    expect(out.map((r) => r.id)).toEqual(['a', 'b']);
  });

  it('filters by engine', () => {
    const out = applyFilters(FIXTURES, { ...FULL_STATE, engine: 'vllm' });
    expect(out).toHaveLength(1);
    expect(out[0].id).toBe('e');
  });

  it('filters by hardware cpu', () => {
    const out = applyFilters(FIXTURES, { ...FULL_STATE, hardware: 'cpu' });
    expect(out.map((r) => r.id)).toEqual(['a', 'b', 'c', 'd']);
  });

  it('filters by hardware gpu', () => {
    const out = applyFilters(FIXTURES, { ...FULL_STATE, hardware: 'gpu' });
    expect(out.map((r) => r.id)).toEqual(['e']);
  });

  it('composes multiple filters (intersection)', () => {
    const out = applyFilters(FIXTURES, { ...FULL_STATE, foundation: 'dev210', engine: 'ollama' });
    expect(out.map((r) => r.id)).toEqual(['a', 'b']);
  });

  it('case-insensitive search on model name', () => {
    const out = applyFilters(FIXTURES, { ...FULL_STATE, search: 'GEMMA4' });
    expect(out.map((r) => r.id)).toEqual(['a', 'b']);
  });

  it('ignores filters with empty string values', () => {
    const out = applyFilters(FIXTURES, { ...FULL_STATE, foundation: '', engine: '' });
    expect(out).toEqual(FIXTURES);
  });

  // ── judgeMode ──────────────────────────────────────────────────────────────

  it('judgeMode full: drops rows where judgeConfigured === false', () => {
    const withUnjudged = [
      mk({ id: 'j1', model: 'model-a', judgeConfigured: true  }),
      mk({ id: 'j2', model: 'model-b', judgeConfigured: false }),
    ];
    const out = applyFilters(withUnjudged, { judgeMode: 'full', sortBy: 'composite' });
    expect(out.map((r) => r.id)).toEqual(['j1']);
  });

  it('judgeMode core: shows all rows including non-judge-configured', () => {
    const withUnjudged = [
      mk({ id: 'j1', model: 'model-a', judgeConfigured: true  }),
      mk({ id: 'j2', model: 'model-b', judgeConfigured: false }),
    ];
    const out = applyFilters(withUnjudged, { judgeMode: 'core', sortBy: 'composite' });
    expect(out.map((r) => r.id)).toEqual(['j1', 'j2']);
  });
});

describe('parseViewParam', () => {
  it('returns composite for null', () => {
    expect(parseViewParam(null)).toBe('composite');
  });
  it('returns composite for undefined', () => {
    expect(parseViewParam(undefined)).toBe('composite');
  });
  it('returns composite for empty string', () => {
    expect(parseViewParam('')).toBe('composite');
  });
  it('returns composite for invalid value', () => {
    expect(parseViewParam('bogus')).toBe('composite');
  });
  it('accepts "composite"', () => {
    expect(parseViewParam('composite')).toBe('composite');
  });
  it('accepts "ttft"', () => {
    expect(parseViewParam('ttft')).toBe('ttft');
  });
  it('accepts "tps"', () => {
    expect(parseViewParam('tps')).toBe('tps');
  });
  it('accepts "accuracy"', () => {
    expect(parseViewParam('accuracy')).toBe('accuracy');
  });
  it('aliases legacy "speed" to "ttft" for backwards compat', () => {
    expect(parseViewParam('speed')).toBe('ttft');
  });
  it('aliases legacy "value" to "composite"', () => {
    expect(parseViewParam('value')).toBe('composite');
  });
  it('is case-sensitive (TTFT !== ttft)', () => {
    expect(parseViewParam('TTFT')).toBe('composite');
  });
  it('DEFAULT_VIEW is composite', () => {
    expect(DEFAULT_VIEW).toBe('composite');
  });
});

describe('parseJudgeModeParam', () => {
  it('returns full for null', () => {
    expect(parseJudgeModeParam(null)).toBe('full');
  });
  it('returns full for undefined', () => {
    expect(parseJudgeModeParam(undefined)).toBe('full');
  });
  it('returns full for empty string', () => {
    expect(parseJudgeModeParam('')).toBe('full');
  });
  it('returns full for unknown value', () => {
    expect(parseJudgeModeParam('bogus')).toBe('full');
  });
  it('accepts "core"', () => {
    expect(parseJudgeModeParam('core')).toBe('core');
  });
  it('accepts "full"', () => {
    expect(parseJudgeModeParam('full')).toBe('full');
  });
  it('DEFAULT_JUDGE_MODE is full', () => {
    expect(DEFAULT_JUDGE_MODE).toBe('full');
  });
});
