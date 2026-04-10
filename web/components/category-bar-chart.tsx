import type { Result, Category } from '../lib/schema';
import { CATEGORIES } from '../lib/schema';

interface Props { result: Result }

export function CategoryBarChart({ result }: Props) {
  const max = 1.0;
  return (
    <div className="space-y-2">
      {CATEGORIES.map((cat) => {
        const cs = result.summary.category_scores.find((c) => c.category === cat);
        const skipped = !cs || cs.status === 'skipped';
        const score = cs?.score ?? 0;
        return (
          <div key={cat} className="flex items-center gap-3 text-sm">
            <div className="w-32 text-right text-muted-foreground">{cat}</div>
            <div className="flex-1 h-6 bg-muted rounded relative">
              {!skipped && (
                <div
                  className="absolute inset-y-0 left-0 bg-primary rounded"
                  style={{ width: `${(score / max) * 100}%` }}
                />
              )}
              {skipped && (
                <div className="absolute inset-0 flex items-center justify-center text-xs text-muted-foreground">
                  skipped (judge not configured)
                </div>
              )}
            </div>
            <div className="w-16 tabular-nums text-right">
              {skipped ? '—' : `${(score * 100).toFixed(0)}%`}
              {cs?.avg_tok_per_sec != null && (
                <div className="text-[10px] text-muted-foreground">
                  {cs.avg_tok_per_sec} tok/s · {Math.round((cs.avg_elapsed_ms ?? 0) / 1000)}s avg
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
