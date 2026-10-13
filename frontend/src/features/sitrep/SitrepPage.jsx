import { Badge, Empty, PageHeader, Panel, Stat } from '../../shared/components/ui';
import { useInvestigation } from '../../store/InvestigationContext';
import { num, pct } from '../../core/utils/format';

export default function SitrepPage() {
  const { d } = useInvestigation();
  if (!d.r) return <><PageHeader kicker="REPORT CENTER" stage="06" title="Situation Report" /><Empty /></>;
  const r = d.r;
  return (
    <div className="space-y-4">
      <PageHeader kicker={`PRIORITY: ${r.risk_level} // RISK SCORE ${num(r.risk_score, 2)}`} stage="06" title={`Incident Situation Report // SITREP-${String(d.id).toUpperCase()}`}
        right={<button className="btn-ghost" onClick={() => window.print()}>Print / save PDF</button>} />
      <Panel title="Conclusion" right={<Badge level={r.risk_level} />}>
        <h2 className="text-lg font-semibold text-white">{r.risk_level} ENVIRONMENTAL RISK (SCORE {num(r.risk_score, 2)})</h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-300">{r.executive_summary}</p>
      </Panel>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel title="Key findings"><ul className="list-disc space-y-1.5 pl-5 text-sm text-slate-300">{r.key_findings.map((f, i) => <li key={i}>{f}</li>)}</ul></Panel>
        <Panel title="Risk indicators"><ul className="list-disc space-y-1.5 pl-5 text-sm text-slate-300">{r.risk_indicators.map((f, i) => <li key={i}>{f}</li>)}</ul></Panel>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Confidence" value={pct(r.confidence)} /><Stat label="Mapped sites" value={d.geo ? d.geo.feature_count : '—'} /><Stat label="Hospitals nearby" value={d.geo ? d.hospitals : '—'} /><Stat label="Evidence cited" value={r.evidence_citations.length} />
      </div>
      <Panel title="Evidence citations"><ul className="space-y-1 font-mono text-[11px] text-slate-500">{r.evidence_citations.map((c) => <li key={c}>{c}</li>)}</ul></Panel>
    </div>
  );
}
