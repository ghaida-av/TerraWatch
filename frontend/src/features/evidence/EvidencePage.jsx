import { useState } from 'react';
import { Bar, BarChart, Cell, ResponsiveContainer, XAxis, YAxis } from 'recharts';
import { Empty, PageHeader, Panel } from '../../shared/components/ui';
import { useInvestigation } from '../../store/InvestigationContext';
import { levelOf, LEVEL } from '../../core/utils/risk';
import { num } from '../../core/utils/format';
import GraphView from './GraphView';

export default function EvidencePage() {
  const { d } = useInvestigation();
  const [sel, setSel] = useState(null);
  if (!d.r) return <><PageHeader kicker="ANALYSIS LAB" stage="04" title="Telemetry & Causal Graph" /><Empty /></>;
  const c = d.c;
  const rows = [['Proximity', c.proximity], ['Wind', c.wind_alignment], ['Air quality', c.air_quality_anomaly], ['Temporal', c.temporal_correlation]].map(([k, v]) => ({ k, v: +num(v, 2), hex: LEVEL[levelOf(v)].hex }));
  return (
    <div className="space-y-4">
      <PageHeader kicker={`AGENTIC CAUSAL ENGINE // #${d.id}`} stage="04" title="Telemetry & Causal Graph" subtitle="Deterministic reasoning graph — the maths runs in Python (geo_analysis/risk.py), never in the LLM." />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_340px]">
        <Panel title={`Evidence graph [${d.g.nodes.length} nodes / ${d.g.relationships.length} links]`}>
          <GraphView graph={d.g} selected={sel} onSelect={setSel} />
          {sel && <pre className="mt-3 max-h-40 overflow-auto rounded bg-void p-3 font-mono text-[11px] text-slate-400">{JSON.stringify(sel, null, 2)}</pre>}
        </Panel>
        <div className="space-y-4">
          <Panel title="Component scores">
            <div className="h-44"><ResponsiveContainer><BarChart data={rows} layout="vertical" margin={{ left: 10 }}><XAxis type="number" domain={[0, 1]} hide /><YAxis type="category" dataKey="k" width={80} tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} /><Bar dataKey="v" radius={4}>{rows.map((r) => <Cell key={r.k} fill={r.hex} />)}</Bar></BarChart></ResponsiveContainer></div>
          </Panel>
          <Panel title="Weighted risk formula">
            <p className="font-mono text-[11px] leading-relaxed text-slate-400">R = 0.25·proximity + 0.30·wind + 0.25·air_quality + 0.20·temporal<br />= 0.25×{num(c.proximity, 2)} + 0.30×{num(c.wind_alignment, 2)} + 0.25×{num(c.air_quality_anomaly, 2)} + 0.20×{num(c.temporal_correlation, 2)} = <b className="text-accent">{num(d.r.risk_score, 3)}</b></p>
          </Panel>
        </div>
      </div>
    </div>
  );
}
