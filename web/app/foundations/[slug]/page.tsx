import { notFound } from 'next/navigation';
import { SiteHeader } from '@/components/site-header';
import { FoundationSummaryCard } from '@/components/foundation-summary-card';
import { LeaderboardTable } from '@/components/leaderboard-table';
import { loadAllResults } from '@/lib/load-results';
import { listFoundations, getFoundationSummary } from '@/lib/foundation-info';
import { enrich } from '@/lib/enriched';

export const dynamicParams = false;

export function generateStaticParams() {
  const slugs = listFoundations(loadAllResults());
  // Return at least a placeholder so Next.js static-export doesn't reject an
  // empty array; the page itself calls notFound() for unknown slugs.
  if (slugs.length === 0) return [{ slug: '__empty__' }];
  return slugs.map((slug) => ({ slug }));
}

export default function FoundationPage({ params }: { params: { slug: string } }) {
  const all = loadAllResults();
  const foundations = listFoundations(all);
  if (!foundations.includes(params.slug)) notFound();

  const summary = getFoundationSummary(all, params.slug);
  const enriched = all
    .map(enrich)
    .filter((r) => r.foundation === params.slug);
  const sorted = [...enriched].sort((a, b) => {
    if (a.composite == null && b.composite == null) return 0;
    if (a.composite == null) return 1;
    if (b.composite == null) return -1;
    return b.composite - a.composite;
  });

  return (
    <>
      <SiteHeader />
      <main className="container py-8 space-y-6">
        <FoundationSummaryCard summary={summary} />
        <LeaderboardTable results={sorted} view="composite" judgeMode="full" />
      </main>
    </>
  );
}
