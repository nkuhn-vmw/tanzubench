import type { Enriched } from '../lib/enriched';
import { CATEGORIES } from '../lib/schema';

interface Props { enriched: Enriched }

/**
 * 10-segment bar strip, one bar per category. Skipped categories
 * render as faint grey bars. Each bar's height encodes its score.
 */
export function CategorySparkline({ enriched }: Props) {
  return (
    <div className="inline-flex items-end gap-0.5 h-6" aria-label="Category scores">
      {CATEGORIES.map((cat) => {
        const cs = enriched.categoryScoresByName[cat];
        const isSkipped = !cs || cs.status === 'skipped';
        const score = cs?.score ?? 0;
        const height = Math.max(2, Math.round((score ?? 0) * 24));
        return (
          <div
            key={cat}
            title={`${cat}: ${isSkipped ? 'skipped' : ((score ?? 0) * 100).toFixed(0) + '%'}`}
            className={`w-1.5 ${isSkipped ? 'bg-muted' : 'bg-primary'}`}
            style={{ height: isSkipped ? 4 : height }}
          />
        );
      })}
    </div>
  );
}
