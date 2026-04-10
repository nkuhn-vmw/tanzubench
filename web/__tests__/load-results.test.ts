import { describe, it, expect } from 'vitest';
import { loadAllResults } from '../lib/load-results';

describe('loadAllResults', () => {
  it('returns an empty array when results/ has no json files', () => {
    const results = loadAllResults();
    // On a fresh checkout, results/ only contains .gitkeep.
    expect(Array.isArray(results)).toBe(true);
  });
});
