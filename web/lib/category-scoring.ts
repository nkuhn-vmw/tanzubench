import type { Result, ResultTest, CategoryScore, Category } from './schema';
import { CATEGORIES, JUDGE_SKIPPED_CATEGORIES } from './schema';

export function isJudgeGraded(result: Result): boolean {
  return result.grading.judge_configured === true;
}

export function categoryScoreFor(result: Result, category: Category): CategoryScore | undefined {
  return result.summary.category_scores.find((c) => c.category === category);
}

export function composite(result: Result): { score: number | null; over: number; max: number } {
  return {
    score: result.summary.composite_score,
    over: result.summary.composite_over,
    max: result.summary.composite_max,
  };
}

export function agenticFrameworkBreakdown(result: Result) {
  return result.summary.agent_framework_scores ?? [];
}

export function testsByCategory(result: Result): Record<Category, ResultTest[]> {
  const out = {} as Record<Category, ResultTest[]>;
  for (const cat of CATEGORIES) {
    out[cat] = [];
  }
  for (const t of result.tests) {
    out[t.category].push(t);
  }
  return out;
}

export function agenticByTask(result: Result): Record<string, ResultTest[]> {
  const out: Record<string, ResultTest[]> = {};
  for (const t of result.tests) {
    if (t.category !== 'agentic') continue;
    // id is "<task>.<framework>"; strip framework
    const taskId = t.agent_framework ? t.id.replace(new RegExp(`\\.${t.agent_framework}$`), '') : t.id;
    (out[taskId] ??= []).push(t);
  }
  return out;
}
