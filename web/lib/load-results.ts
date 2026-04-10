import fs from 'fs';
import path from 'path';
import { ResultSchema, type Result } from './schema';

export interface LoadedResult {
  id: string;             // stable derived id (relative path without .json)
  path: string;           // filesystem path relative to repo root
  result: Result;
}

const RESULTS_ROOT = path.resolve(process.cwd(), '../results');

export function loadAllResults(): LoadedResult[] {
  if (!fs.existsSync(RESULTS_ROOT)) return [];
  const out: LoadedResult[] = [];
  walk(RESULTS_ROOT, (file) => {
    if (!file.endsWith('.json')) return;
    const raw = fs.readFileSync(file, 'utf8');
    let parsed: unknown;
    try {
      parsed = JSON.parse(raw);
    } catch (e) {
      throw new Error(`invalid JSON in ${file}: ${(e as Error).message}`);
    }
    const result = ResultSchema.parse(parsed);
    // Derive a single-segment id from the relative path. Next.js dynamic
    // routes are single-segment by default, and our /result/[id] route
    // cannot match ids containing forward slashes — so flatten with
    // double-underscores. `tdc/gpu/foo-...` → `tdc__gpu__foo-...`.
    const rel = path.relative(RESULTS_ROOT, file).replace(/\.json$/, '');
    const id = rel.split(path.sep).join('__');
    out.push({ id, path: path.relative(path.resolve(process.cwd(), '..'), file), result });
  });
  return out;
}

function walk(dir: string, cb: (file: string) => void): void {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name.startsWith('.')) continue;
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(p, cb);
    else cb(p);
  }
}
