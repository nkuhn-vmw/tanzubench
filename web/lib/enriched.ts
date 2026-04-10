import type { LoadedResult } from './load-results';
import type { Result, Category, CategoryScore } from './schema';
import { CATEGORIES } from './schema';
import { composite, isJudgeGraded, agenticFrameworkBreakdown } from './category-scoring';

export interface Enriched {
  id: string;
  model: string;
  modelDisplay: string;
  foundation: string;
  hardware: 'cpu' | 'gpu';
  composite: number | null;
  compositeOver: number;
  judgeConfigured: boolean;
  categoryScoresByName: Record<Category, CategoryScore | undefined>;
  result: Result;
  path: string;
}

export function enrich(loaded: LoadedResult): Enriched {
  const r = loaded.result;
  const hardware: 'cpu' | 'gpu' = r.hardware.gpu_count > 0 ? 'gpu' : 'cpu';
  const byName = {} as Record<Category, CategoryScore | undefined>;
  for (const cat of CATEGORIES) {
    byName[cat] = r.summary.category_scores.find((c) => c.category === cat);
  }
  const c = composite(r);
  return {
    id: loaded.id,
    model: r.target.name,
    modelDisplay: r.target.display_name ?? r.target.name,
    foundation: r.meta.foundation,
    hardware,
    composite: c.score,
    compositeOver: c.over,
    judgeConfigured: isJudgeGraded(r),
    categoryScoresByName: byName,
    result: r,
    path: loaded.path,
  };
}
