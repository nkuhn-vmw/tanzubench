'use client';

import { cn } from '@/lib/utils';

interface SegmentedControlOption<T extends string> {
  value: T;
  label: string;
}

interface SegmentedControlProps<T extends string> {
  label?: string;
  options: SegmentedControlOption<T>[];
  value: T;
  onChange: (value: T) => void;
  ariaLabel?: string;
}

/**
 * A horizontal segmented control — like radio buttons that look like a
 * pill switcher. All options are visible at once (no dropdown), so users
 * can switch with one click and see the full set of choices upfront.
 *
 * Used for small enums (3-5 options): Engine (Ollama/vLLM), Hardware
 * (CPU/GPU), View (Speed/Accuracy).
 */
export function SegmentedControl<T extends string>({
  label,
  options,
  value,
  onChange,
  ariaLabel,
}: SegmentedControlProps<T>) {
  return (
    <div className="flex items-center gap-2">
      {label && (
        <span className="text-sm font-medium text-muted-foreground select-none">
          {label}
        </span>
      )}
      <div
        role="radiogroup"
        aria-label={ariaLabel ?? label}
        className="inline-flex items-center rounded-md border border-border bg-background p-0.5"
      >
        {options.map((opt) => {
          const selected = value === opt.value;
          return (
            <button
              key={opt.value}
              role="radio"
              aria-checked={selected}
              type="button"
              onClick={() => onChange(opt.value)}
              className={cn(
                'px-3 py-1.5 text-sm font-medium rounded-sm transition-colors',
                selected
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground hover:bg-accent',
              )}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
