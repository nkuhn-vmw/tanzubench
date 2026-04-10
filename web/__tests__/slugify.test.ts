import { describe, it, expect } from 'vitest';
import { pathToSlug } from '@/lib/slugify';

describe('pathToSlug', () => {
  it('produces a URL-safe slug from a results path', () => {
    const slug = pathToSlug('results/dev210/cpu/2026-04-06_gemma4-e4b_cpu-2xlarge.json');
    expect(slug).toMatch(/^[a-z0-9-]+$/);
    expect(slug).toContain('dev210');
    expect(slug).toContain('gemma4-e4b');
  });

  it('is deterministic', () => {
    const a = pathToSlug('results/dev210/cpu/file.json');
    const b = pathToSlug('results/dev210/cpu/file.json');
    expect(a).toBe(b);
  });

  it('is unique per path', () => {
    const a = pathToSlug('results/dev210/cpu/a.json');
    const b = pathToSlug('results/dev210/cpu/b.json');
    expect(a).not.toBe(b);
  });

  it('strips .json extension', () => {
    const slug = pathToSlug('results/cdc/cpu/x.json');
    expect(slug).not.toContain('.json');
    expect(slug).not.toContain('json');
  });

  it('replaces underscores and slashes with dashes', () => {
    const slug = pathToSlug('results/dev210/cpu/2026-04-06_gemma4-e4b_cpu-2xlarge.json');
    expect(slug).not.toContain('_');
    expect(slug).not.toContain('/');
  });
});
