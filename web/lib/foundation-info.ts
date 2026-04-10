import type { LoadedResult } from './load-results';

export interface FoundationSummary {
  slug: string;
  resultCount: number;
  vmTypes: string[];
  engines: { name: string; version?: string }[];
  gpuModels: string[];
  hasCpu: boolean;
  hasGpu: boolean;
}

export function listFoundations(results: LoadedResult[]): string[] {
  return Array.from(new Set(results.map((r) => r.result.meta.foundation))).sort();
}

export function getFoundationSummary(results: LoadedResult[], slug: string): FoundationSummary {
  const forFoundation = results.filter((r) => r.result.meta.foundation === slug);
  const vmTypes = Array.from(
    new Set(forFoundation.map((r) => r.result.hardware.vm_type).filter((x): x is string => !!x)),
  ).sort();
  const engines = Array.from(
    new Map(
      forFoundation.map((r) => [
        `${r.result.engine.name}:${r.result.engine.version ?? ''}`,
        { name: r.result.engine.name, version: r.result.engine.version ?? undefined },
      ]),
    ).values(),
  );
  const gpuModels = Array.from(
    new Set(forFoundation.map((r) => r.result.hardware.gpu_model).filter((x): x is string => !!x)),
  ).sort();
  return {
    slug,
    resultCount: forFoundation.length,
    vmTypes,
    engines,
    gpuModels,
    hasCpu: forFoundation.some((r) => r.result.hardware.gpu_count === 0),
    hasGpu: forFoundation.some((r) => r.result.hardware.gpu_count > 0),
  };
}
