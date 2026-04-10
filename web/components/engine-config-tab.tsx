'use client';
import type { Result } from '../lib/schema';

export function EngineConfigTab({ result }: { result: Result }) {
  const cfg = result.engine.config;
  const json = JSON.stringify(cfg, null, 2);
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">
          {result.engine.name} {result.engine.version ?? ''}
        </h3>
        <button
          className="text-xs border rounded px-2 py-1"
          onClick={() => navigator.clipboard.writeText(json)}
        >
          Copy JSON
        </button>
      </div>
      {cfg._error ? (
        <div className="text-sm text-red-500 border border-red-500/30 rounded p-3">
          Engine metadata unavailable: {String(cfg._error)}
        </div>
      ) : (
        <pre className="text-xs bg-muted p-3 rounded overflow-auto">{json}</pre>
      )}
      <p className="text-xs text-muted-foreground">
        Source: <code>{String(cfg._source ?? 'unknown')}</code>
      </p>
    </div>
  );
}
