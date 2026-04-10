/**
 * Convert a result file path into a stable, URL-safe slug suitable for
 * `/result/[id]` routing. The slug preserves enough of the path to be
 * unique across the repo but is lowercased, dash-separated, and safe
 * to use in URLs.
 */
export function pathToSlug(filePath: string): string {
  return filePath
    .replace(/^results\//, '')
    .replace(/\.json$/, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}
