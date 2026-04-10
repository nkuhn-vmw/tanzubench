'use client';

interface Props {
  value: 'full' | 'core';
  onChange: (value: 'full' | 'core') => void;
}

export function JudgeModeToggle({ value, onChange }: Props) {
  return (
    <div className="inline-flex rounded-md border text-sm" role="radiogroup"
         aria-label="Judge mode">
      <button
        role="radio"
        aria-checked={value === 'full'}
        className={`px-3 py-1.5 ${value === 'full' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground'}`}
        onClick={() => onChange('full')}
      >
        Full (judge-graded)
      </button>
      <button
        role="radio"
        aria-checked={value === 'core'}
        className={`px-3 py-1.5 ${value === 'core' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground'}`}
        onClick={() => onChange('core')}
      >
        Core (deterministic)
      </button>
    </div>
  );
}
