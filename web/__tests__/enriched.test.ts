import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { ResultSchema } from '../lib/schema';
import { enrich } from '../lib/enriched';

const raw = JSON.parse(fs.readFileSync(
  path.resolve(__dirname, 'fixtures/v2-full.json'), 'utf8'));
const result = ResultSchema.parse(raw);
const loaded = { id: 'tdc/gpu/qwen3-32b', path: 'results/tdc/gpu/qwen3-32b.json', result };

describe('enrich', () => {
  it('derives hardware from gpu_count', () => {
    expect(enrich(loaded).hardware).toBe('gpu');
  });
  it('exposes composite', () => {
    expect(enrich(loaded).composite).toBe(1.0);
  });
  it('exposes judgeConfigured', () => {
    expect(enrich(loaded).judgeConfigured).toBe(true);
  });
});
