import type { Result } from '@/lib/schema';

export function ResultTestsTab({ result }: { result: Result }) {
  return (
    <div className="rounded-lg border mt-4 overflow-hidden">
      <div className="grid grid-cols-[2fr_1fr_1fr_1fr_1fr_1fr_1fr] px-4 py-2 bg-muted text-[10px] uppercase font-semibold text-muted-foreground border-b">
        <div>Test</div>
        <div>Category</div>
        <div>Grader</div>
        <div className="text-right">Score</div>
        <div>Status</div>
        <div className="text-right">Elapsed</div>
        <div className="text-right">Tokens</div>
      </div>
      {result.tests.map((t, i) => (
        <div
          key={`${t.id}-${i}`}
          className="grid grid-cols-[2fr_1fr_1fr_1fr_1fr_1fr_1fr] px-4 py-2 border-b last:border-0 text-xs items-center"
        >
          <div className="font-medium">{t.name}</div>
          <div className="text-muted-foreground">{t.category}</div>
          <div className="text-muted-foreground">{t.grader}</div>
          <div className="text-right num">{(t.score * 100).toFixed(0)}%</div>
          <div>{t.status}</div>
          <div className="text-right num">
            {t.elapsed_ms != null ? `${(t.elapsed_ms / 1000).toFixed(2)}s` : '—'}
          </div>
          <div className="text-right num">{t.completion_tokens ?? '—'}</div>
        </div>
      ))}
    </div>
  );
}
