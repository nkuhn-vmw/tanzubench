import type { FoundationSummary } from '@/lib/foundation-info';

export function FoundationSummaryCard({ summary }: { summary: FoundationSummary }) {
  return (
    <div className="rounded-lg border p-5 bg-muted/30">
      <h2 className="text-xl font-bold uppercase">{summary.slug}</h2>
      <div className="text-xs text-muted-foreground mt-1">{summary.resultCount} benchmark results</div>
      <div className="grid md:grid-cols-2 gap-4 mt-4 text-xs">
        <div>
          <div className="font-semibold text-muted-foreground text-[10px] uppercase mb-1">VM Types</div>
          <div>{summary.vmTypes.length ? summary.vmTypes.join(', ') : '—'}</div>
        </div>
        <div>
          <div className="font-semibold text-muted-foreground text-[10px] uppercase mb-1">Engines</div>
          <div>
            {summary.engines.length
              ? summary.engines.map((e) => `${e.name} ${e.version ?? ''}`.trim()).join(', ')
              : '—'}
          </div>
        </div>
        {summary.gpuModels.length > 0 && (
          <div>
            <div className="font-semibold text-muted-foreground text-[10px] uppercase mb-1">GPUs</div>
            <div>{summary.gpuModels.join(', ')}</div>
          </div>
        )}
        <div>
          <div className="font-semibold text-muted-foreground text-[10px] uppercase mb-1">Compute</div>
          <div>
            {[summary.hasCpu && 'CPU', summary.hasGpu && 'GPU'].filter(Boolean).join(' + ') || '—'}
          </div>
        </div>
      </div>
    </div>
  );
}
