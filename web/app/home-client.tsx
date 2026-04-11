'use client';

import { useSearchParams } from 'next/navigation';
import { FilterBar } from '@/components/filter-bar';
import { LeaderboardTable } from '@/components/leaderboard-table';
import {
  applyFilters,
  type FilterState,
} from '@/lib/filters';
import { enrich, type Enriched } from '@/lib/enriched';
import type { LoadedResult } from '@/lib/load-results';

export function HomeClient({ results }: { results: LoadedResult[] }) {
  const params = useSearchParams();

  // Enrich all loaded results first.
  const enriched: Enriched[] = results.map(enrich);

  const filters: FilterState = {
    engine: params.get('engine') ?? undefined,
    hardware: (params.get('hw') as 'cpu' | 'gpu') ?? undefined,
    search: params.get('q') ?? undefined,
  };

  const filtered = applyFilters(enriched, filters);

  // Sort by composite descending; null composites sink to the bottom.
  const sorted = [...filtered].sort((a, b) => {
    if (a.composite == null && b.composite == null) return 0;
    if (a.composite == null) return 1;
    if (b.composite == null) return -1;
    return b.composite - a.composite;
  });

  return (
    <>
      <FilterBar />
      <div className="container py-6 md:py-8">
        <LeaderboardTable results={sorted} />
        <div className="flex flex-col sm:flex-row sm:justify-between gap-1 text-sm text-muted-foreground mt-4">
          <div>
            Showing <span className="text-foreground font-semibold">{sorted.length}</span>{' '}
            result{sorted.length === 1 ? '' : 's'}
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
