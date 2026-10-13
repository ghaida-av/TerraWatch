import { Badge, Empty, PageHeader, Panel, Stat } from '../../shared/components/ui';
import { useInvestigation } from '../../store/InvestigationContext';
import { levelStyle } from '../../core/utils/risk';
import { num, pct } from '../../core/utils/format';
import { buildVectors } from './vectors';

export default function RiskPage() {
  const { d } = useInvestigation();
  if (!d.r) return <><PageHeader kicker="ANALYSIS LAB" stage="03" title="Risk Overview" /><Empty /></>;
  const s = levelStyle(d.r.risk_level);
  return (
    <div className="space-y-4">
      <PageHeader kicker={`${d.r.risk_level} ADVISORY // SITREP ${d.id}`} stage="03" title="Risk Overview" right={<Badge level={d.r.risk_level}>{pct(d.r.confidence)} CONFIDENCE</Badge>} />
      <Panel>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-[220px_1fr]">
          <div className="panel-2 grid place-items-center p-4 text-center"><div className="label">Risk level</div><div className={`font-mono text-4xl font-bold ${s.text}`}>{d.r.risk_level}</div><div className="mt-1 font-mono text-sm text-slate-400">score {num(d.r.risk_score, 2)}</div></div>
          <div><div className="label">Executive summary</div><p className="mt-2 text-sm leading-relaxed text-slate-300">{d.r.executive_summary}</p></div>
        </div>
      </Panel>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {buildVectors(d).map((v) => (
          <Panel key={v.title} title={v.title} right={<Badge level={v.level} />}>
            <div className="flex items-baseline gap-2"><span className={`font-mono text-4xl font-semibold ${levelStyle(v.level).text}`}>{v.big}</span><span className="text-xs text-slate-500">{v.unit}</span></div>
            <div className="mt-1 text-sm text-slate-400">{v.state}</div>
            {!!v.rows.length && <dl className="mt-3 space-y-1.5">{v.rows.map(([k, val]) => <div key={k} className="flex justify-between border-b border-line/60 pb-1 text-sm"><dt className="label !tracking-wider">{k}</dt><dd className="font-mono text-slate-200">{val}</dd></div>)}</dl>}
            <p className="mt-3 text-xs text-slate-500">{v.note}</p>
          </Panel>
        ))}
      </div>
    </div>
  );
}
