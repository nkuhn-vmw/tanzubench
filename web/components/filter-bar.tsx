'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SegmentedControl } from '@/components/segmented-control';

type EngineFilter = 'all' | 'ollama' | 'vllm';
type HwFilter = 'all' | 'cpu' | 'gpu';

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

  function reset() {
    router.replace('?', { scroll: false });
  }

  const engineValue = (params.get('engine') as EngineFilter) ?? 'all';
  const hwValue = (params.get('hw') as HwFilter) ?? 'all';
  const searchValue = params.get('q') ?? '';

  const hasActiveFilter =
    engineValue !== 'all' || hwValue !== 'all' || searchValue !== '';

  return (
    <div className="bg-muted border-b">
      <div className="container py-4">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
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

          <div className="hidden md:block md:flex-1" />

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
