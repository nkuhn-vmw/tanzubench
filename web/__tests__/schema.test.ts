import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { ResultSchema } from '../lib/schema';

const FIXTURES = path.resolve(__dirname, 'fixtures');

describe('ResultSchema v2', () => {
  it('parses a full judge-configured result', () => {
    const raw = JSON.parse(fs.readFileSync(path.join(FIXTURES, 'v2-full.json'), 'utf8'));
    const result = ResultSchema.parse(raw);
    expect(result.schema_version).toBe('2.0.0');
    expect(result.grading.judge_configured).toBe(true);
    expect(result.summary.composite_score).toBe(1.0);
  });

  it('parses a core-only judgeless result', () => {
    const raw = JSON.parse(fs.readFileSync(path.join(FIXTURES, 'v2-core-only.json'), 'utf8'));
    const result = ResultSchema.parse(raw);
    expect(result.grading.judge_configured).toBe(false);
    expect(result.grading.skipped_categories).toContain('writing');
  });

  it('rejects missing required field', () => {
    const raw = JSON.parse(fs.readFileSync(path.join(FIXTURES, 'v2-full.json'), 'utf8'));
    delete raw.grading;
    expect(() => ResultSchema.parse(raw)).toThrow();
  });
});
