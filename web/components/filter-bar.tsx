'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SegmentedControl } from '@/components/segmented-control';
import { JudgeModeToggle } from '@/components/judge-mode-toggle';
import {
  DEFAULT_VIEW,
  DEFAULT_JUDGE_MODE,
  parseViewParam,
  parseJudgeModeParam,
  type ViewName,
  type JudgeMode,
} from '@/lib/filters';

type EngineFilter = 'all' | 'ollama' | 'vllm';
type HwFilter = 'all' | 'cpu' | 'gpu';

const VIEW_OPTIONS: { value: ViewName; label: string }[] = [
  { value: 'composite', label: 'Composite' },
  { value: 'tps', label: 'Tok/s' },
];

const ENGINE_OPTIONS: { value: EngineFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'ollama', label: 'Ollama' },
  { value: 'vllm', label: 'vLLM' },
];

const HARDWARE_OPTIONS: { value: HwFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'cpu', label: 'CPU' },
  { value: 'gpu', label: 'GPU' },
];

export function FilterBar() {
  const router = useRouter();
  const params = useSearchParams();

  function setParam(key: string, value: string | null) {
    const next = new URLSearchParams(Array.from(params.entries()));
    if (!value || value === 'all') next.delete(key);
    else next.set(key, value);
    const qs = next.toString();
    router.replace(qs ? `?${qs}` : '?', { scroll: false });
  }

  function setView(view: ViewName) {
    const next = new URLSearchParams(Array.from(params.entries()));
    if (view === DEFAULT_VIEW) next.delete('view');
    else next.set('view', view);
    const qs = next.toString();
    router.replace(qs ? `?${qs}` : '?', { scroll: false });
  }

  function setJudgeMode(mode: JudgeMode) {
    const next = new URLSearchParams(Array.from(params.entries()));
    if (mode === DEFAULT_JUDGE_MODE) next.delete('judge');
    else next.set('judge', mode);
    const qs = next.toString();
    router.replace(qs ? `?${qs}` : '?', { scroll: false });
  }

  function reset() {
    const view = params.get('view');
    router.replace(view ? `?view=${view}` : '?', { scroll: false });
  }

  const viewValue = parseViewParam(params.get('view'));
  const judgeModeValue = parseJudgeModeParam(params.get('judge'));
  const engineValue = (params.get('engine') as EngineFilter) ?? 'all';
  const hwValue = (params.get('hw') as HwFilter) ?? 'all';
  const searchValue = params.get('q') ?? '';

  const hasActiveFilter =
    engineValue !== 'all' || hwValue !== 'all' || searchValue !== '' ||
    judgeModeValue !== DEFAULT_JUDGE_MODE;

  return (
    <div className="bg-muted border-b">
      <div className="container py-4">
        {/* Segmented controls: wrap to a 2nd line on mobile if needed */}
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          <SegmentedControl<ViewName>
            label="View"
            options={VIEW_OPTIONS}
            value={viewValue}
            onChange={setView}
          />
          <SegmentedControl<EngineFilter>
            label="Engine"
            options={ENGINE_OPTIONS}
            value={engineValue}
            onChange={(v) => setParam('engine', v)}
          />
          <SegmentedControl<HwFilter>
            label="Hardware"
            options={HARDWARE_OPTIONS}
            value={hwValue}
            onChange={(v) => setParam('hw', v)}
          />

          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Scoring
            </span>
            <JudgeModeToggle value={judgeModeValue} onChange={setJudgeMode} />
          </div>

          {/* Spacer only applies at md+ where the search sits inline */}
          <div className="hidden md:block md:flex-1" />

          {/* Search */}
          <div className="relative w-full md:w-64 mt-3 md:mt-0">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none"
              aria-hidden="true"
            />
            <input
              type="search"
              placeholder="Search models..."
              value={searchValue}
              onChange={(e) => setParam('q', e.target.value)}
              className="h-10 w-full rounded-md border border-input bg-background pl-9 pr-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="Search model"
            />
          </div>

          {hasActiveFilter && (
            <Button
              variant="ghost"
              size="sm"
              onClick={reset}
              className="mt-3 md:mt-0"
            >
              Reset
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
