import type { Result } from '../lib/schema';
import { CategoryBarChart } from './category-bar-chart';
import { testsByCategory } from '../lib/category-scoring';

export function ResultCategoriesTab({ result }: { result: Result }) {
  const grouped = testsByCategory(result);
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-medium mb-3">Category scores</h3>
        <CategoryBarChart result={result} />
      </div>
      <div>
        <h3 className="text-sm font-medium mb-3">Individual tests</h3>
        {Object.entries(grouped).map(([cat, tests]) => {
          if (tests.length === 0) return null;
          return (
            <details key={cat} className="border rounded mb-2">
              <summary className="cursor-pointer px-3 py-2 text-sm">
                {cat} ({tests.length} tests)
              </summary>
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-muted-foreground">
                    <th className="px-3 py-1">Test</th>
                    <th className="px-3 py-1">Status</th>
                    <th className="px-3 py-1">Score</th>
                    <th className="px-3 py-1">Details</th>
                  </tr>
                </thead>
                <tbody>
                  {tests.map((t) => (
                    <tr key={t.id} className="border-t">
                      <td className="px-3 py-1">{t.name}</td>
                      <td className="px-3 py-1">{t.status}</td>
                      <td className="px-3 py-1 tabular-nums">
                        {(t.score * 100).toFixed(0)}%
                      </td>
                      <td className="px-3 py-1 font-mono text-xs truncate max-w-md">
                        {JSON.stringify(t.details).slice(0, 80)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
          );
        })}
      </div>
    </div>
  );
}
