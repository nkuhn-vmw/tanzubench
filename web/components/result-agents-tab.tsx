import type { Result } from '../lib/schema';
import { AgentComparisonChart } from './agent-comparison-chart';
import { agenticFrameworkBreakdown } from '../lib/category-scoring';

export function ResultAgentsTab({ result }: { result: Result }) {
  const fw = agenticFrameworkBreakdown(result);
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-medium mb-3">Framework averages</h3>
        <div className="flex gap-4">
          {fw.map((f) => (
            <div key={f.framework} className="border rounded p-3">
              <div className="text-xs text-muted-foreground">{f.framework}</div>
              <div className="text-2xl tabular-nums">{(f.score * 100).toFixed(0)}%</div>
              <div className="text-xs text-muted-foreground">over {f.tasks} tasks</div>
            </div>
          ))}
        </div>
      </div>
      <div>
        <h3 className="text-sm font-medium mb-3">Per-task breakdown</h3>
        <AgentComparisonChart result={result} />
      </div>
    </div>
  );
}
