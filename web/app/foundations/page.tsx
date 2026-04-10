import Link from 'next/link';
import { SiteHeader } from '@/components/site-header';
import { FoundationSummaryCard } from '@/components/foundation-summary-card';
import { loadAllResults } from '@/lib/load-results';
import { listFoundations, getFoundationSummary } from '@/lib/foundation-info';

export default function FoundationsIndex() {
  const results = loadAllResults();
  const foundations = listFoundations(results);
  return (
    <>
      <SiteHeader />
      <main className="container py-8">
        <h1 className="text-2xl font-bold mb-2">Foundations</h1>
        <p className="text-sm text-muted-foreground mb-6">
          Every Tanzu foundation that has contributed benchmark results to this leaderboard.
        </p>
        <div className="grid md:grid-cols-2 gap-4">
          {foundations.map((f) => (
            <Link key={f} href={`/foundations/${f}`} className="block hover:opacity-90">
              <FoundationSummaryCard summary={getFoundationSummary(results, f)} />
            </Link>
          ))}
        </div>
      </main>
    </>
  );
}
