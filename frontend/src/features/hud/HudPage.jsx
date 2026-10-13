import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis } from 'recharts';
import { Badge, Empty, PageHeader, Panel, Stat } from '../../shared/components/ui';
import { useInvestigation } from '../../store/InvestigationContext';
import { SRC_LABEL } from '../dispatch/constants';
import { hudLines } from './hudLines';
import { hhmmss, num, pct } from '../../core/utils/format';

export default function HudPage() {
  const { S, d } = useInvestigation();
  const last = S.events.at(-1);
  const times = S.stageT.map((t, i) => ({ step: i + 1, ms: t - (i ? S.stageT[i - 1] : S.t0) }));
  const state = S.running ? 'STREAMING' : S.runErr ? 'FAILED' : d.r ? 'COMPLETE' : 'IDLE';

  return (
    <div className="space-y-4">
      <PageHeader kicker={`AGENTIC RUNTIME // THREAD #${d.id || '—'}`} stage="02" title={S.running ? 'Autonomous Investigation in Progress' : d.r ? 'Autonomous Investigation Complete' : 'Autonomous Investigation Idle'}
        subtitle={S.runErr || last?.message || 'Dispatch an investigation from the Launchpad to stream live progress.'} right={<Badge level={S.runErr ? 'CRITICAL' : S.running ? 'MODERATE' : d.r ? 'LOW' : 'IDLE'}>{state}</Badge>} />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Steps" value={`${S.events.length} / 8`} />
        <Stat label="Elapsed" value={S.running ? `${((Date.now() - S.t0) / 1000).toFixed(1)}s` : S.lastDur ? `${(S.lastDur / 1000).toFixed(2)}s` : '—'} />
        <Stat label="Confidence" value={pct(d.r?.confidence)} />
        <Stat label="Risk level" value={d.r?.risk_level || '—'} level={d.r?.risk_level} />
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3 xl:grid-cols-5">
        {Object.keys(SRC_LABEL).map((src) => {
          const ev = d.ev[src], asked = S.reqSources.includes(src) || !!ev;
          const [t, a, b] = hudLines(src, ev, d, asked, S.running);
          const badge = !asked ? ['NOT QUERIED', 'IDLE'] : !ev ? ['QUERYING', 'MODERATE'] : ev.status === 'ok' ? ['VERIFIED', 'LOW'] : ['ERROR', 'CRITICAL'];
          return (
            <Panel key={src} title={SRC_LABEL[src]} right={<Badge level={badge[1]}>{badge[0]}</Badge>}>
              <div className="text-xs text-slate-500">{t}</div><div className="mt-1 text-sm font-medium text-slate-100">{a}</div><div className="mt-1 font-mono text-[11px] text-slate-500">{b}</div>
            </Panel>
          );
        })}
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_340px]">
        <Panel title={`Agentic reasoning stream // ${S.events.length}-step execution log`}>
          {!S.events.length ? <Empty>No events yet. Dispatch an investigation to stream live progress from the backend.</Empty> : (
            <ol className="space-y-2">
              {S.events.map((e, i) => (
                <li key={i} className="panel-2 p-3">
                  <div className="flex justify-between font-mono text-[11px]"><span className="text-accent">STEP {String(i + 1).padStart(2, '0')} // {e.stage.toUpperCase()}</span><span className="text-slate-500">{hhmmss(S.stageT[i] || Date.now())}</span></div>
                  <p className="mt-1 text-sm text-slate-300">{e.message}{e.report ? ` — ${e.report.executive_summary}` : ''}</p>
                </li>
              ))}
            </ol>
          )}
        </Panel>
        <div className="space-y-4">
          <Panel title="Stage durations (ms)">
            <div className="h-32"><ResponsiveContainer><BarChart data={times}><XAxis dataKey="step" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} /><YAxis hide /><Bar dataKey="ms" fill="#22d3ee" radius={[3, 3, 0, 0]} /></BarChart></ResponsiveContainer></div>
          </Panel>
          <Panel title="Payload">
            <pre className="max-h-64 overflow-auto rounded bg-void p-3 font-mono text-[11px] text-slate-400">{d.r ? JSON.stringify({ session_id: d.r.investigation_id, target: d.r.target, risk: { level: d.r.risk_level, score: num(d.r.risk_score, 3), confidence: d.r.confidence }, components: d.c, signals: d.sig }, null, 2) : '{ }'}</pre>
          </Panel>
        </div>
      </div>
    </div>
  );
}
