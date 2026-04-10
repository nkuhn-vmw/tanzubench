import { Suspense } from 'react';
import { SiteHeader } from '@/components/site-header';
import { loadAllResults } from '@/lib/load-results';
import { HomeClient } from './home-client';

export default function HomePage() {
  const results = loadAllResults();
  return (
    <>
      <SiteHeader />
      <main>
        <div className="container py-8 md:py-10">
          <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold mb-3 tracking-tight">
            What&apos;s the best model for agentic inference on Tanzu Platform?
          </h1>
          <p className="text-sm sm:text-base text-muted-foreground max-w-2xl leading-relaxed">
            Open benchmarks for LLMs running on the Tanzu GenAI tile. CPU + GPU, Ollama + vLLM,
            across real Tanzu Platform foundations.
          </p>
        </div>
        <Suspense fallback={null}>
          <HomeClient results={results} />
        </Suspense>
      </main>
    </>
  );
}
