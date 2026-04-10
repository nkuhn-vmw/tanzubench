'use client';

import { useSearchParams } from 'next/navigation';
import { FilterBar } from '@/components/filter-bar';
import { LeaderboardTable } from '@/components/leaderboard-table';
import {
  applyFilters,
  parseViewParam,
  parseJudgeModeParam,
  type FilterState,
} from '@/lib/filters';
import { enrich, type Enriched } from '@/lib/enriched';
import type { LoadedResult } from '@/lib/load-results';

export function HomeClient({ results }: { results: LoadedResult[] }) {
  const params = useSearchParams();
  const view = parseViewParam(params.get('view'));
  const judgeMode = parseJudgeModeParam(params.get('judge'));

  // Enrich all loaded results first.
  const enriched: Enriched[] = results.map(enrich);

  const filters: FilterState = {
    engine: params.get('engine') ?? undefined,
    hardware: (params.get('hw') as 'cpu' | 'gpu') ?? undefined,
    search: params.get('q') ?? undefined,
    judgeMode,
    sortBy: view,
  };

  const filtered = applyFilters(enriched, filters);

  // Sort based on the active view.
  let sorted: Enriched[];
  let resultLabel: string;

  if (view === 'composite') {
    sorted = [...filtered].sort((a, b) => {
      // Null composites sink to the bottom
      if (a.composite == null && b.composite == null) return 0;
      if (a.composite == null) return 1;
      if (b.composite == null) return -1;
      return b.composite - a.composite;
    });
    resultLabel = 'composite';
  } else if (view === 'accuracy') {
    // For accuracy view, sort by composite descending (composite_score is the accuracy proxy in v2)
    sorted = [...filtered].sort((a, b) => {
      if (a.composite == null && b.composite == null) return 0;
      if (a.composite == null) return 1;
      if (b.composite == null) return -1;
      return b.composite - a.composite;
    });
    resultLabel = 'accuracy';
  } else if (view === 'tps') {
    sorted = [...filtered].sort((a, b) => {
      const aTps = tokPerSec(a);
      const bTps = tokPerSec(b);
      if (aTps == null && bTps == null) return 0;
      if (aTps == null) return 1;
      if (bTps == null) return -1;
      return bTps - aTps;
    });
    resultLabel = 'throughput';
  } else {
    // ttft — no native TTFT in v2 suite results; sort by composite as proxy
    sorted = [...filtered].sort((a, b) => {
      if (a.composite == null && b.composite == null) return 0;
      if (a.composite == null) return 1;
      if (b.composite == null) return -1;
      return b.composite - a.composite;
    });
    resultLabel = 'TTFT';
  }

  return (
    <>
      <FilterBar />
      <div className="container py-6 md:py-8">
        <LeaderboardTable results={sorted} view={view} judgeMode={judgeMode} />
        <div className="flex flex-col sm:flex-row sm:justify-between gap-1 text-sm text-muted-foreground mt-4">
          <div>
            Showing <span className="text-foreground font-semibold">{sorted.length}</span>{' '}
            {resultLabel} result{sorted.length === 1 ? '' : 's'}
          </div>
          <div>
            Last updated{' '}
            {new Date().toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'short',
              day: 'numeric',
            })}
          </div>
        </div>
      </div>
    </>
  );
}

function tokPerSec(e: Enriched): number | null {
  const s = e.result.summary;
  if (s.total_tokens != null && s.total_time_ms != null && s.total_time_ms > 0) {
    return (s.total_tokens / s.total_time_ms) * 1000;
  }
  return null;
}
