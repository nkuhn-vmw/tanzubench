import { notFound } from 'next/navigation';
import { SiteHeader } from '@/components/site-header';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ResultCategoriesTab } from '@/components/result-categories-tab';
import { ResultAgentsTab } from '@/components/result-agents-tab';
import { EngineConfigTab } from '@/components/engine-config-tab';
import { ResultTestsTab } from '@/components/result-tests-tab';
import { ResultConfigTab } from '@/components/result-config-tab';
import { ResultRawTab } from '@/components/result-raw-tab';
import { loadAllResults } from '@/lib/load-results';

export const dynamicParams = false;

export function generateStaticParams() {
  const results = loadAllResults();
  // Return at least a placeholder so Next.js static-export doesn't reject an
  // empty array; the page itself calls notFound() for unknown ids.
  if (results.length === 0) return [{ id: '__empty__' }];
  return results.map((r) => ({ id: r.id }));
}

export default function ResultPage({ params }: { params: { id: string } }) {
  const all = loadAllResults();
  const loaded = all.find((r) => r.id === params.id);
  if (!loaded) notFound();

  const result = loaded.result;

  const hasAgentic = result.summary.category_scores.some(
    (c) => c.category === 'agentic' && c.status === 'scored'
  );

  return (
    <>
      <SiteHeader />
      <main className="container py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold">{result.target.name}</h1>
          <div className="flex flex-wrap gap-2 mt-2 text-[11px]">
            <Badge>{result.meta.foundation}</Badge>
            <Badge>{result.engine.name} {result.engine.version}</Badge>
            <Badge>
              {result.hardware.vm_type ??
                (result.hardware.gpu_count > 0 ? `${result.hardware.gpu_count} GPU` : 'CPU')}
            </Badge>
            <Badge>{result.result_type}</Badge>
          </div>
          <div className="text-xs text-muted-foreground mt-2">
            {new Date(result.meta.timestamp).toLocaleString()}
          </div>
        </div>

        <Tabs defaultValue="categories">
          <TabsList>
            <TabsTrigger value="categories">Categories</TabsTrigger>
            {hasAgentic && <TabsTrigger value="agents">Agent Comparison</TabsTrigger>}
            <TabsTrigger value="engine">Engine Config</TabsTrigger>
            <TabsTrigger value="tests">Tests</TabsTrigger>
            <TabsTrigger value="config">Config</TabsTrigger>
            <TabsTrigger value="raw">Raw</TabsTrigger>
          </TabsList>
          <TabsContent value="categories">
            <ResultCategoriesTab result={result} />
          </TabsContent>
          {hasAgentic && (
            <TabsContent value="agents">
              <ResultAgentsTab result={result} />
            </TabsContent>
          )}
          <TabsContent value="engine">
            <EngineConfigTab result={result} />
          </TabsContent>
          <TabsContent value="tests">
            <ResultTestsTab result={result} />
          </TabsContent>
          <TabsContent value="config">
            <ResultConfigTab result={result} />
          </TabsContent>
          <TabsContent value="raw">
            <ResultRawTab result={result} path={loaded.path} />
          </TabsContent>
        </Tabs>
      </main>
    </>
  );
}

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-medium bg-muted">
      {children}
    </span>
  );
}
