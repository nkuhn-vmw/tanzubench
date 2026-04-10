import type { Result } from '@/lib/schema';

export function ResultRawTab({ result, path }: { result: Result; path: string }) {
  return (
    <div className="mt-4">
      <div className="text-xs text-muted-foreground mb-2">Source: {path}</div>
      <pre className="rounded-lg border bg-muted p-4 text-[11px] font-mono overflow-x-auto">
        {JSON.stringify(result, null, 2)}
      </pre>
    </div>
  );
}
