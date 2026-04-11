'use client';

import Link from 'next/link';
import { RankMedal } from '@/components/rank-medal';
import { cn } from '@/lib/utils';
import type { Enriched } from '@/lib/enriched';
import { CategorySparkline } from '@/components/category-sparkline';

interface LeaderboardTableProps {
  results: Enriched[];
}

function formatComposite(score: number | null | undefined): string {
  if (score == null) return '—';
  return score.toFixed(2);
}

function formatDate(isoTimestamp: string): string {
  return new Date(isoTimestamp.slice(0, 10)).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Compose the subtitle from whatever target-metadata fields are actually
 * populated. Returns an empty string if nothing is available — callers
 * should not render a subtitle row in that case (no dash placeholders;
 * users drill into /result/[id] for full metadata).
 */
function formatModelSubtitle(target: {
  architecture?: string | null;
  quant?: string | null;
  size_gb?: number | null;
}): string {
  const parts: string[] = [];
  if (target.architecture) parts.push(target.architecture);
  if (target.quant) parts.push(target.quant);
  if (target.size_gb != null) parts.push(`${target.size_gb} GB`);
  return parts.join(' · ');
}

/** Tiny CPU/GPU pill. */
function HardwareBadge({ hardware }: { hardware: 'cpu' | 'gpu' }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
        hardware === 'gpu'
          ? 'bg-violet-500/15 text-violet-700 dark:text-violet-300'
          : 'bg-sky-500/15 text-sky-700 dark:text-sky-300',
      )}
    >
      {hardware.toUpperCase()}
    </span>
  );
}

export function LeaderboardTable({ results }: LeaderboardTableProps) {
  if (results.length === 0) {
    return (
      <div className="rounded-lg border p-8 md:p-12 text-center text-muted-foreground text-base leaderboard-panel">
        No results match the current filters. Try resetting or broadening them.
      </div>
    );
  }

  return (
    <>
      <DesktopTable results={results} />
      <MobileCardList results={results} />
    </>
  );
}

// ─── Desktop grid ────────────────────────────────────────────────────────────

function DesktopTable({ results }: { results: Enriched[] }) {
  return (
    <div className="hidden md:block rounded-lg border overflow-hidden leaderboard-panel">
      <div className="grid grid-cols-[48px_2.4fr_1.6fr_1fr_1.6fr_1fr] px-5 py-3 bg-muted text-xs uppercase tracking-wider font-semibold text-muted-foreground border-b">
        <div>#</div>
        <div>Model</div>
        <div>Foundation</div>
        <div>Engine</div>
        <div className="text-right text-foreground">Composite</div>
        <div className="text-right">Date</div>
      </div>
      {results.map((r, i) => {
        const rank = i + 1;
        const res = r.result;
        const subtitle = formatModelSubtitle(res.target);
        const tps = r.result.summary.total_tokens != null && r.result.summary.total_time_ms != null && r.result.summary.total_time_ms > 0
          ? ((r.result.summary.total_tokens / r.result.summary.total_time_ms) * 1000).toFixed(1)
          : null;
        return (
          <Link
            key={r.id}
            href={`/result/${r.id}`}
            className="grid grid-cols-[48px_2.4fr_1.6fr_1fr_1.6fr_1fr] px-5 py-4 items-center border-b last:border-0 hover:bg-accent transition-colors"
          >
            <div>
              <RankMedal rank={rank} />
            </div>
            <div>
              <div className="font-semibold text-base flex items-center gap-2 text-foreground">
                {r.modelDisplay}
                <HardwareBadge hardware={r.hardware} />
              </div>
              {subtitle && (
                <div className="text-xs text-muted-foreground mt-0.5">{subtitle}</div>
              )}
            </div>
            <div>
              <div className="text-sm text-foreground font-medium">{r.foundation}</div>
              {tps && (
                <div className="text-xs text-muted-foreground mt-0.5">
                  {tps} tok/s avg
                </div>
              )}
            </div>
            <div className="text-sm text-foreground">{res.engine.name}</div>
            {/* Composite column */}
            <div className="text-right text-lg font-bold">
              <div className={cn(
                'num tabular-nums inline-flex items-center',
                rank <= 3 && 'text-emerald-600 dark:text-emerald-400',
              )}>
                {formatComposite(r.composite)}
              </div>
              {r.composite != null && (
                <div className="mt-1 flex justify-end">
                  <CategorySparkline enriched={r} />
                </div>
              )}
            </div>
            <div className="text-right text-xs text-muted-foreground">
              {formatDate(r.result.meta.timestamp)}
            </div>
          </Link>
        );
      })}
    </div>
  );
}

// ─── Mobile card list ────────────────────────────────────────────────────────

function MobileCardList({ results }: { results: Enriched[] }) {
  return (
    <div className="md:hidden flex flex-col gap-3">
      {results.map((r, i) => {
        const rank = i + 1;
        const res = r.result;

        const headlineValue = formatComposite(r.composite);

        return (
          <Link
            key={r.id}
            href={`/result/${r.id}`}
            className="block rounded-lg border bg-background p-4 hover:bg-accent active:bg-accent transition-colors leaderboard-panel"
          >
            {/* Row 1: rank + name + badges + prominent headline value */}
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3 min-w-0 flex-1">
                <div className="shrink-0 pt-0.5">
                  <RankMedal rank={rank} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="font-semibold text-base text-foreground flex items-center gap-2 flex-wrap">
                    <span className="truncate">{r.modelDisplay}</span>
                    <HardwareBadge hardware={r.hardware} />
                  </div>
                  {formatModelSubtitle(res.target) && (
                    <div className="text-xs text-muted-foreground mt-0.5 truncate">
                      {formatModelSubtitle(res.target)}
                    </div>
                  )}
                </div>
              </div>
              <div
                className={cn(
                  'shrink-0 text-right text-xl font-bold num tabular-nums',
                  rank <= 3 && 'text-emerald-600 dark:text-emerald-400',
                )}
              >
                {headlineValue}
              </div>
            </div>

            {/* Row 2: foundation + engine. We skip hardware spec detail
                (vm_type / cpu_cores / ram_gb) on the card — those live
                on /result/[id] now to avoid empty '—' placeholders. */}
            <div className="mt-3 text-xs text-muted-foreground">
              <span className="text-foreground font-medium">{r.foundation}</span>
              {' · '}
              <span className="text-foreground">{res.engine.name}</span>
            </div>

            {/* Row 3: composite sparkline */}
            {r.composite != null && (
              <div className="mt-3 pt-3 border-t border-border flex items-center gap-2">
                <span className="text-xs text-muted-foreground">Categories:</span>
                <CategorySparkline enriched={r} />
              </div>
            )}

            {/* Date */}
            <div className="mt-2 text-xs text-muted-foreground text-right">
              {formatDate(res.meta.timestamp)}
            </div>
          </Link>
        );
      })}
    </div>
  );
}
