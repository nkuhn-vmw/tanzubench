import { cn } from '@/lib/utils';

interface RankMedalProps {
  rank: number;
}

const MEDAL_COLORS: Record<number, string> = {
  1: 'bg-yellow-400 text-yellow-950',
  2: 'bg-slate-300 text-slate-900',
  3: 'bg-amber-600 text-amber-50',
};

export function RankMedal({ rank }: RankMedalProps) {
  if (rank <= 3) {
    return (
      <span
        className={cn(
          'inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold',
          MEDAL_COLORS[rank],
        )}
        aria-label={`Rank ${rank}`}
      >
        {rank}
      </span>
    );
  }
  return (
    <span className="text-sm text-muted-foreground" aria-label={`Rank ${rank}`}>
      {rank}
    </span>
  );
}
