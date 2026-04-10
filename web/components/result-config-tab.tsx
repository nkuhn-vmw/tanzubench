import type { Result } from '@/lib/schema';

function Row({ label, value }: { label: string; value: unknown }) {
  if (value == null || value === '') return null;
  return (
    <div className="grid grid-cols-[160px_1fr] gap-2 py-1.5 text-xs border-b last:border-0">
      <div className="text-muted-foreground">{label}</div>
      <div className="num">
        {typeof value === 'object' ? JSON.stringify(value) : String(value)}
      </div>
    </div>
  );
}

export function ResultConfigTab({ result }: { result: Result }) {
  const grading = result.grading;
  return (
    <div className="grid md:grid-cols-2 gap-6 mt-4">
      <div className="rounded-lg border p-4">
        <h3 className="font-semibold text-sm mb-2">Hardware</h3>
        <Row label="VM Type" value={result.hardware.vm_type} />
        <Row label="CPU" value={result.hardware.cpu} />
        <Row label="CPU Cores" value={result.hardware.cpu_cores} />
        <Row label="RAM" value={result.hardware.ram_gb ? `${result.hardware.ram_gb} GB` : null} />
        <Row label="GPU Count" value={result.hardware.gpu_count} />
        <Row label="GPU Model" value={result.hardware.gpu_model} />
        <Row
          label="GPU Memory"
          value={result.hardware.gpu_memory_gb ? `${result.hardware.gpu_memory_gb} GB` : null}
        />
        <Row
          label="Power Limit"
          value={result.hardware.power_limit_watts ? `${result.hardware.power_limit_watts}W` : null}
        />
      </div>
      <div className="rounded-lg border p-4">
        <h3 className="font-semibold text-sm mb-2">Grading</h3>
        <Row label="Judge configured" value={grading.judge_configured ? 'yes' : 'no'} />
        <Row label="Judge model" value={grading.judge_model} />
        <Row label="Judge endpoint" value={grading.judge_endpoint} />
        <Row label="Judge fingerprint" value={grading.judge_fingerprint} />
        <Row
          label="Skipped categories"
          value={grading.skipped_categories.length > 0 ? grading.skipped_categories.join(', ') : 'none'}
        />
      </div>
      <div className="rounded-lg border p-4 md:col-span-2">
        <h3 className="font-semibold text-sm mb-2">Target &amp; Meta</h3>
        <Row label="Model" value={result.target.name} />
        <Row label="Display name" value={result.target.display_name} />
        <Row label="Family" value={result.target.family} />
        <Row label="Architecture" value={result.target.architecture} />
        <Row label="Parameters" value={result.target.parameters_b != null ? `${result.target.parameters_b}B` : null} />
        <Row label="Quant" value={result.target.quant} />
        <Row label="Foundation" value={result.meta.foundation} />
        <Row label="Tile version" value={result.meta.tile_version} />
        <Row label="Tag" value={result.meta.tag} />
        <Row label="Notes" value={result.meta.notes} />
      </div>
    </div>
  );
}
