import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { HomeClient } from '@/app/home-client';
import type { LoadedResult } from '@/lib/load-results';
import type { Result } from '@/lib/schema';

// useSearchParams is replaced per-test via the mockParams variable below.
let mockParams = new URLSearchParams();
vi.mock('next/navigation', () => ({
  useSearchParams: () => mockParams,
  useRouter: () => ({ replace: vi.fn() }),
}));

beforeEach(() => {
  mockParams = new URLSearchParams();
  cleanup();
});

// Minimal valid v2 Result factory
function makeResult(overrides: {
  name: string;
  foundation?: string;
  gpuCount?: number;
  compositeScore?: number;
  judgeConfigured?: boolean;
  totalTokens?: number;
  totalTimeMs?: number;
}): Result {
  const {
    name,
    foundation = 'tdc',
    gpuCount = 2,
    compositeScore = 0.9,
    judgeConfigured = true,
    totalTokens = 100,
    totalTimeMs = 5000,
  } = overrides;
  return {
    schema_version: '2.0.0',
    result_type: 'suite',
    meta: {
      timestamp: '2026-04-08T14:00:00Z',
      foundation,
    },
    target: { name },
    engine: {
      name: 'vllm',
      version: '0.6.3',
      config: { _source: 'test' },
    },
    hardware: {
      gpu_count: gpuCount,
      gpu_model: gpuCount > 0 ? 'RTX 3090' : undefined,
    },
    grading: {
      judge_configured: judgeConfigured,
      skipped_categories: judgeConfigured ? [] : ['reasoning', 'writing', 'research'],
    },
    tests: [
      {
        id: 'basic-math-1',
        name: 'Multiply',
        category: 'basic',
        grader: 'exact_match',
        score: compositeScore,
        max_score: 1.0,
        status: 'scored',
        agent_framework: null,
        completion_tokens: 3,
        elapsed_ms: 120,
        details: {},
      },
    ],
    summary: {
      headline_metric: 'composite_score',
      headline_value: compositeScore,
      composite_score: compositeScore,
      composite_max: 1.0,
      composite_over: 1,
      total_tokens: totalTokens,
      total_time_ms: totalTimeMs,
      category_scores: [
        { category: 'basic', score: compositeScore, max: 1.0, tasks: 1, status: 'scored' },
      ],
    },
  };
}

function makeLoaded(id: string, overrides: Parameters<typeof makeResult>[0]): LoadedResult {
  return {
    id,
    path: `results/tdc/gpu/${id}.json`,
    result: makeResult(overrides),
  };
}

// Two judge-configured (full) results for baseline tests
const fullFixture: LoadedResult[] = [
  makeLoaded('gemma4', { name: 'gemma4:e4b', compositeScore: 0.95 }),
  makeLoaded('qwen3', { name: 'qwen3-32b', compositeScore: 0.80 }),
];

// One judge-configured, one not — for judge filtering tests
const mixedFixture: LoadedResult[] = [
  makeLoaded('full-model', { name: 'full-model', judgeConfigured: true, compositeScore: 0.90 }),
  makeLoaded('core-model', { name: 'core-model', judgeConfigured: false, compositeScore: 0.85 }),
];

describe('HomeClient — composite view (default)', () => {
  it('renders without throwing', () => {
    render(<HomeClient results={fullFixture} />);
    expect(screen.getAllByText('gemma4:e4b').length).toBeGreaterThan(0);
  });

  it('shows the result count in the footer', () => {
    render(<HomeClient results={fullFixture} />);
    const matches = screen.getAllByText((_content, element) => {
      const text = element?.textContent ?? '';
      return /Showing\s+2\s+results/i.test(text);
    });
    expect(matches.length).toBeGreaterThan(0);
  });

  it('sorts composite results highest first', () => {
    render(<HomeClient results={fullFixture} />);
    const links = screen.getAllByRole('link');
    const linkTexts = links.map((l) => l.textContent ?? '');
    const gemmaIdx = linkTexts.findIndex((t) => t.includes('gemma4:e4b'));
    const qwenIdx = linkTexts.findIndex((t) => t.includes('qwen3-32b'));
    expect(gemmaIdx).toBeGreaterThanOrEqual(0);
    expect(qwenIdx).toBeGreaterThanOrEqual(0);
    // gemma4 has score 0.95 > qwen3 0.80 → should appear first
    expect(gemmaIdx).toBeLessThan(qwenIdx);
  });

  it('renders empty state when no results match', () => {
    render(<HomeClient results={[]} />);
    expect(screen.getByText(/no results match/i)).toBeInTheDocument();
  });
});

describe('HomeClient — judge filtering (hardcoded full mode)', () => {
  it('always hides rows where judgeConfigured === false', () => {
    render(<HomeClient results={mixedFixture} />);
    expect(screen.getAllByText('full-model').length).toBeGreaterThan(0);
    expect(screen.queryAllByText('core-model').length).toBe(0);
  });
});
