import type { Enriched } from '../lib/enriched';
import { CATEGORIES } from '../lib/schema';

function colorFor(score: number | null): string {
  if (score === null) return 'bg-muted';
  if (score >= 0.9) return 'bg-green-600';
  if (score >= 0.7) return 'bg-green-400';
  if (score >= 0.5) return 'bg-yellow-400';
  if (score >= 0.3) return 'bg-orange-400';
  return 'bg-red-400';
}

export function CategoryHeatmap({ rows }: { rows: Enriched[] }) {
  return (
    <table className="text-xs">
      <thead>
        <tr>
          <th className="text-left p-2">Model</th>
          {CATEGORIES.map((cat) => (
            <th key={cat} className="p-1 text-center text-muted-foreground">
              {cat.slice(0, 6)}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.id}>
            <td className="p-2 font-medium">
              {r.modelDisplay} <span className="text-muted-foreground">({r.foundation}/{r.hardware})</span>
            </td>
            {CATEGORIES.map((cat) => {
              const cs = r.categoryScoresByName[cat];
              const score = cs?.score ?? null;
              return (
                <td key={cat} className="p-1">
                  <div
                    className={`w-10 h-6 ${colorFor(score)} rounded text-center text-[10px] flex items-center justify-center text-white`}
                    title={`${cat}: ${score === null ? 'skipped' : (score * 100).toFixed(0) + '%'}`}
                  >
                    {score === null ? '—' : Math.round(score * 100)}
                  </div>
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
