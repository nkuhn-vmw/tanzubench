import { Suspense } from 'react';
import { SiteHeader } from '@/components/site-header';
import { CompareClient } from './compare-client';
import { loadAllResults } from '@/lib/load-results';

export default function ComparePage() {
  const results = loadAllResults();
  return (
    <>
      <SiteHeader />
      <main className="container py-10">
        <h1 className="text-3xl md:text-4xl font-bold mb-3 tracking-tight">
          Compare results side by side
        </h1>
        <p className="text-base text-muted-foreground mb-8 max-w-2xl">
          Pick up to 4 benchmark results from the dropdown below and see their headline
          metric and per-test breakdown next to each other. The selection is encoded in
          the URL so you can share or bookmark it.
        </p>
        <Suspense fallback={null}>
          <CompareClient allResults={results} />
        </Suspense>
      </main>
    </>
  );
}
