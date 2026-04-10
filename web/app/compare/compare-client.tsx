'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { LoadedResult } from '@/lib/load-results';
import { enrich } from '@/lib/enriched';
import { CategoryHeatmap } from '@/components/category-heatmap';

const MAX_COMPARE = 4;

function formatHeadline(r: LoadedResult): string {
  const summary = r.result.summary;
  const unit = summary.headline_unit;
  const value = summary.headline_value;
  if (unit === '%') return `${Math.round(value)}%`;
  if (value >= 1000) return `${(value / 1000).toFixed(2)}s`;
  return `${Math.round(value)}ms`;
}

function formatTestValue(test: { elapsed_ms?: number | null; tok_per_sec?: number | null; score?: number }): string {
  if (test.score != null) return `${(test.score * 100).toFixed(0)}%`;
  if (test.elapsed_ms != null) {
    return test.elapsed_ms >= 1000
      ? `${(test.elapsed_ms / 1000).toFixed(2)}s`
      : `${Math.round(test.elapsed_ms)}ms`;
  }
  if (test.tok_per_sec != null) return `${test.tok_per_sec.toFixed(1)} tok/s`;
  return '—';
}

export function CompareClient({ allResults }: { allResults: LoadedResult[] }) {
  const router = useRouter();
  const params = useSearchParams();
  const ids = (params.get('ids') ?? '').split(',').filter(Boolean);
  const selected = ids
    .map((id) => allResults.find((r) => r.id === id))
    .filter((r): r is LoadedResult => !!r);

  function setIds(nextIds: string[]) {
    if (nextIds.length === 0) {
      router.replace('?', { scroll: false });
    } else {
      router.replace(`?ids=${nextIds.join(',')}`, { scroll: false });
    }
  }

  function addResult(id: string) {
    if (!id || ids.includes(id) || ids.length >= MAX_COMPARE) return;
    setIds([...ids, id]);
  }

  function removeResult(id: string) {
    setIds(ids.filter((x) => x !== id));
  }

  function clearAll() {
    setIds([]);
  }

  // Pool of results not yet selected, grouped roughly by foundation for nicer browsing
  const available = allResults
    .filter((r) => !ids.includes(r.id))
    .sort((a, b) => {
      const cmp = a.result.meta.foundation.localeCompare(b.result.meta.foundation);
      if (cmp !== 0) return cmp;
      return a.result.target.name.localeCompare(b.result.target.name);
    });

  const selectionFull = selected.length >= MAX_COMPARE;
  const enrichedRows = selected.map(enrich);

  // Build the union of test names across selected results so the table
  // has a row for every test that appears in any of them.
  const allTestNames = Array.from(
    new Set(selected.flatMap((r) => r.result.tests.map((t) => t.name))),
  ).sort();

  return (
    <div className="space-y-6">
      {/* Picker row: dropdown + clear */}
      <div className="rounded-lg border bg-muted/30 p-4">
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-sm font-medium" htmlFor="add-result">
            Add a result
          </label>
          <select
            id="add-result"
            className="h-10 flex-1 min-w-[280px] rounded-md border border-input bg-background px-3 text-sm disabled:opacity-50"
            value=""
            onChange={(e) => {
              addResult(e.target.value);
              e.target.value = '';
            }}
            disabled={selectionFull}
            aria-label="Add a result to compare"
          >
            <option value="">
              {selectionFull
                ? `Maximum ${MAX_COMPARE} results selected`
                : 'Pick a model to compare...'}
            </option>
            {available.map((r) => (
              <option key={r.id} value={r.id}>
                {r.result.target.name} — {r.result.meta.foundation} · {r.result.engine.name}{' '}
                {r.result.engine.version ?? ''} · {r.result.result_type}
              </option>
            ))}
          </select>
          {selected.length > 0 && (
            <Button variant="ghost" size="sm" onClick={clearAll}>
              Clear all
            </Button>
          )}
        </div>

        {/* Selected chips */}
        {selected.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-4">
            {selected.map((r) => (
              <div
                key={r.id}
                className="inline-flex items-center gap-2 rounded-full border border-border bg-background pl-3 pr-1 py-1 text-sm"
              >
                <span className="font-semibold">{r.result.target.name}</span>
                <span className="text-muted-foreground text-xs">
                  · {r.result.meta.foundation} · {r.result.engine.name}
                </span>
                <button
                  onClick={() => removeResult(r.id)}
                  className="ml-1 inline-flex h-5 w-5 items-center justify-center rounded-full hover:bg-accent"
                  aria-label={`Remove ${r.result.target.name}`}
                  type="button"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Table or empty state */}
      {selected.length === 0 ? (
        <div className="rounded-lg border p-12 text-center text-muted-foreground leaderboard-panel">
          <p className="text-base">
            Pick at least 2 results from the dropdown above to compare them side by side.
          </p>
          <p className="text-sm mt-2">
            You can compare up to {MAX_COMPARE} results across all of their test metrics.
          </p>
        </div>
      ) : selected.length === 1 ? (
        <div className="rounded-lg border p-12 text-center text-muted-foreground leaderboard-panel">
          <p className="text-base">
            <strong className="text-foreground">{selected[0].result.target.name}</strong> selected.
            Add at least one more result to see a comparison.
          </p>
        </div>
      ) : (
        <>
        <section className="mb-6">
          <h2 className="text-lg font-medium mb-3">Category scores</h2>
          <CategoryHeatmap rows={enrichedRows} />
        </section>
        <div className="rounded-lg border overflow-hidden leaderboard-panel">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted">
                <tr>
                  <th className="text-left px-4 py-3 text-xs uppercase font-semibold text-muted-foreground">
                    Metric
                  </th>
                  {selected.map((r) => (
                    <th key={r.id} className="text-right px-4 py-3">
                      <div className="font-semibold text-base text-foreground">
                        {r.result.target.name}
                      </div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {r.result.meta.foundation} · {r.result.hardware.vm_type ?? '—'}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {r.result.engine.name} {r.result.engine.version ?? ''}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {/* Headline row — what the leaderboard sorts on */}
                <tr className="border-t bg-accent/30">
                  <td className="px-4 py-3 font-semibold">Headline</td>
                  {selected.map((r) => (
                    <td
                      key={r.id}
                      className="text-right px-4 py-3 num tabular-nums font-bold text-base"
                    >
                      {formatHeadline(r)}
                    </td>
                  ))}
                </tr>

                {/* Per-test rows */}
                {allTestNames.map((name) => (
                  <tr key={name} className="border-t">
                    <td className="px-4 py-3 font-medium">{name}</td>
                    {selected.map((r) => {
                      const test = r.result.tests.find((t) => t.name === name);
                      return (
                        <td
                          key={r.id}
                          className="text-right px-4 py-3 num tabular-nums"
                        >
                          {test ? formatTestValue(test) : '—'}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        </>
      )}
    </div>
  );
}
