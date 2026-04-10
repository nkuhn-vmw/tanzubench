import { cn } from '@/lib/utils';

interface VariantBadgeProps {
  label: string;
  className?: string;
}

export function VariantBadge({ label, className }: VariantBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium bg-primary/10 text-primary',
        className,
      )}
    >
      {label}
    </span>
  );
}
