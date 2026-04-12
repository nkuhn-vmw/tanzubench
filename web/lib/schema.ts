import { z } from 'zod';

export const SCHEMA_VERSION = '2.0.0' as const;

export const CATEGORIES = [
  'basic', 'tool_use', 'structured_output', 'coding', 'debugging',
  'long_context', 'instruction', 'file_ops', 'multi_turn',
  'reasoning', 'writing', 'research', 'monitoring', 'iac', 'ci_repair', 'repo_patch', 'sysadmin', 'agentic',
] as const;
export type Category = typeof CATEGORIES[number];

export const JUDGE_SKIPPED_CATEGORIES: Category[] = ['reasoning', 'writing', 'research'];

const MetaSchema = z.object({
  timestamp: z.string().datetime(),
  foundation: z.string().min(1),
  tile_version: z.string().nullable().optional(),
  tag: z.string().nullable().optional(),
  notes: z.string().nullable().optional(),
  source_file: z.string().nullable().optional(),
}).strict();

const TargetSchema = z.object({
  name: z.string().min(1),
  display_name: z.string().nullable().optional(),
  family: z.string().nullable().optional(),
  parameters_b: z.number().nonnegative().nullable().optional(),
  active_parameters_b: z.number().nonnegative().nullable().optional(),
  architecture: z.string().nullable().optional(),
  quant: z.string().nullable().optional(),
  size_gb: z.number().nonnegative().nullable().optional(),
}).strict();

const EngineSchema = z.object({
  name: z.enum(['ollama', 'vllm', 'other']),
  version: z.string().nullable().optional(),
  config: z.record(z.any()),
}).strict();

const HardwareSchema = z.object({
  vm_type: z.string().nullable().optional(),
  cpu: z.string().nullable().optional(),
  cpu_cores: z.number().int().nonnegative().nullable().optional(),
  ram_gb: z.union([z.number(), z.string()]).nullable().optional(),
  gpu_count: z.number().int().nonnegative(),
  gpu_model: z.string().nullable().optional(),
  gpu_memory_gb: z.number().nonnegative().nullable().optional(),
  power_limit_watts: z.number().int().nonnegative().nullable().optional(),
}).strict();

const GradingSchema = z.object({
  judge_configured: z.boolean(),
  judge_model: z.string().nullable().optional(),
  judge_endpoint: z.string().nullable().optional(),
  judge_fingerprint: z.string().nullable().optional(),
  judge_run_date: z.string().datetime().nullable().optional(),
  skipped_categories: z.array(z.string()),
}).strict();

const JudgeDetailSchema = z.object({}).passthrough().nullable();

const TestSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  category: z.enum(CATEGORIES),
  grader: z.enum(['exact_match', 'contains', 'regex', 'tool_call', 'needle',
                   'file_check', 'exec_unit_tests', 'llm_judge', 'json_schema', 'multi_turn', 'exec_build', 'container_exec', 'agentic']),
  score: z.number().min(0).max(1),
  max_score: z.number().nonnegative(),
  status: z.enum(['scored', 'skipped', 'timeout', 'error']),
  agent_framework: z.enum(['opencode', 'aider', 'custom']).nullable(),
  prompt_tokens: z.number().int().nonnegative().nullable().optional(),
  completion_tokens: z.number().int().nonnegative().nullable().optional(),
  elapsed_ms: z.number().nonnegative().nullable().optional(),
  tok_per_sec: z.number().nonnegative().nullable().optional(),
  details: z.record(z.any()),
  judge: JudgeDetailSchema.optional(),
  raw_response: z.string().nullable().optional(),
  notes: z.string().nullable().optional(),
}).strict();

const CategoryScoreSchema = z.object({
  category: z.string().min(1),
  score: z.number().min(0).max(1).nullable(),
  max: z.number().nonnegative(),
  tasks: z.number().int().nonnegative(),
  status: z.enum(['scored', 'skipped']),
  avg_tok_per_sec: z.number().nonnegative().nullable().optional(),
  avg_elapsed_ms: z.number().nonnegative().nullable().optional(),
}).strict();

const AgentFrameworkScoreSchema = z.object({
  framework: z.enum(['opencode', 'aider', 'custom']),
  score: z.number().min(0).max(1),
  tasks: z.number().int().nonnegative(),
}).strict();

const SummarySchema = z.object({
  headline_metric: z.string().min(1),
  headline_value: z.number().nonnegative(),
  headline_unit: z.string().nullable().optional(),
  composite_score: z.number().min(0).max(1).nullable(),
  composite_max: z.number().nonnegative(),
  composite_over: z.number().int().nonnegative(),
  total_tokens: z.number().int().nonnegative().nullable().optional(),
  total_time_ms: z.number().nonnegative().nullable().optional(),
  category_scores: z.array(CategoryScoreSchema),
  agent_framework_scores: z.array(AgentFrameworkScoreSchema).nullable().optional(),
}).strict();

export const ResultSchema = z.object({
  schema_version: z.literal(SCHEMA_VERSION),
  result_type: z.enum(['suite', 'speed', 'accuracy', 'scale', 'comparison']),
  meta: MetaSchema,
  target: TargetSchema,
  engine: EngineSchema,
  hardware: HardwareSchema,
  grading: GradingSchema,
  tests: z.array(TestSchema).min(1),
  summary: SummarySchema,
}).strict();

export type Result = z.infer<typeof ResultSchema>;
export type ResultTest = z.infer<typeof TestSchema>;
export type CategoryScore = z.infer<typeof CategoryScoreSchema>;
export type AgentFrameworkScore = z.infer<typeof AgentFrameworkScoreSchema>;
