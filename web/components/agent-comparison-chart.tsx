import type { Result } from '../lib/schema';
import { agenticByTask } from '../lib/category-scoring';

const FRAMEWORK_COLORS: Record<string, string> = {
  aider: 'bg-blue-500',
  opencode: 'bg-purple-500',
  custom: 'bg-green-500',
};

export function AgentComparisonChart({ result }: { result: Result }) {
  const byTask = agenticByTask(result);
  const tasks = Object.keys(byTask);
  if (tasks.length === 0) {
    return <p className="text-sm text-muted-foreground">No agentic tests ran.</p>;
  }
  return (
    <div className="space-y-4">
      {tasks.map((taskId) => {
        const rows = byTask[taskId];
        return (
          <div key={taskId}>
            <div className="text-sm font-medium mb-2">{taskId}</div>
            <div className="grid grid-cols-3 gap-2">
              {rows.map((r) => (
                <div key={r.id} className="border rounded p-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium">{r.agent_framework}</span>
                    <span className={`inline-block w-2 h-2 rounded-full ${FRAMEWORK_COLORS[r.agent_framework ?? 'custom']}`} />
                  </div>
                  <div className="text-2xl tabular-nums mt-1">
                    {(r.score * 100).toFixed(0)}%
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {r.status}
                    {typeof r.details?.elapsed_sec === 'number' &&
                      ` · ${Math.round(r.details.elapsed_sec)}s`}
                    {typeof r.details?.turns_completed === 'number' &&
                      ` · ${r.details.turns_completed} turns`}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
