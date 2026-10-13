import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Stat } from '../../shared/components/ui';
import { ProgressionChart, SectorChart } from '../../shared/components/Charts';
import { useInvestigation } from '../../store/InvestigationContext';
import { useGlobalEvents } from '../monitor/useGlobalEvents';
import { PRESETS, SRC_LABEL, TIERS } from './constants';
import { clock, gmtStamp, progression, sectorCounts, topLevel } from '../../core/utils/events';
import { lat$, lon$, num } from '../../core/utils/format';

const RING = { LOW: 'border-emerald-400', MODERATE: 'border-yellow-300', HIGH: 'border-orange-400', CRITICAL: 'border-red-400' };
const HEAD = { CRITICAL: 'from-red-500/30 text-red-300', HIGH: 'from-red-500/25 text-orange-300', MODERATE: 'from-amber-500/20 text-amber-300', LOW: 'from-emerald-500/20 text-emerald-300' };

export default function DispatchPage() {
  const { S, d, startInvestigation } = useInvestigation();
  const nav = useNavigate();
  const incoming = useLocation().state; // e.g. coming from the map's "Investigate area" button
  const [form, setForm] = useState({ location: 'Cairo', country: 'Egypt', tier: 2, question: 'Investigate acute environmental threats, thermal anomalies around Cairo right now' });
  const set = (p) => setForm((f) => ({ ...f, ...p }));
  const { data: feed } = useGlobalEvents({ window: 'day', minMag: 2.5 });
  useEffect(() => { if (incoming?.location) set({ location: incoming.location, country: '' }); }, [incoming]);

  const events = feed?.events || [];
  const sectors = useMemo(() => sectorCounts(events), [events]);
  const series = useMemo(() => progression(events, 'day'), [events]);
  const strongest = useMemo(() => [...events].sort((a, b) => (b.magnitude || 0) - (a.magnitude || 0))[0], [events]);
  const level = d.r?.risk_level || topLevel(feed?.summary?.levels) || 'LOW';
  const headline = d.r ? `${d.r.risk_level} RISK - ${d.target?.name?.toUpperCase()}` : feed ? `${topLevel(feed.summary.levels) === 'LOW' ? 'NOMINAL' : 'ELEVATED THREAT'} - ${feed.total} EVENTS ACTIVE` : 'CONNECTING…';

  const run = () => {
    if (!form.location.trim() || S.running) return;
    startInvestigation({ location: form.location.trim(), question: form.question.trim() || 'What environmental risks exist?', sources: TIERS[form.tier].sources, countryHint: form.country.trim() });
    nav('/hud');
  };

  return (
    <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1fr_21rem]">
      <div className="space-y-5">
        <div className="pt-2">
          <div className="flex items-center gap-3 font-mono text-[11px] tracking-wider text-slate-300"><span className="h-2 w-2 rounded-full bg-violet-400" />PLANETARY SEISMIC NETWORK <span className="text-slate-500">| NGS:84</span></div>
          <div className="mt-2 flex items-center gap-2 font-mono text-[11px] tracking-wider text-cyan-300"><span className="h-2 w-2 rounded-full bg-cyan-400" />STAGE 01 ·</div>
          <h1 className="mt-1 text-4xl font-bold text-white">Autonomous Investigation Launchpad</h1>
          <p className="mt-1 max-w-xl text-[15px] text-slate-400">Initiate multi-vector environmental crisis inquiries across heterogeneous telemetry feeds.</p>
          <div className="mt-4 border-b border-white/10" />
        </div>

        <section className="card p-5">
          <div className="flex items-center justify-between">
            <h3 className="font-mono text-[12px] tracking-[0.18em] text-cyan-300">01 INVESTIGATION QUERY</h3>
            <span className={`flex items-center gap-2 rounded-md border px-3 py-1 font-mono text-[11px] ${S.offline ? 'border-red-400/40 bg-red-500/10 text-red-300' : 'border-emerald-400/40 bg-emerald-500/10 text-emerald-300'}`}><span className={`h-2 w-2 rounded-full ${S.offline ? 'bg-red-400' : 'bg-emerald-400'}`} />{S.offline ? 'AGENT OFFLINE' : 'AI AGENT READY'}</span>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-[1fr_15rem]">
            <div className="rounded-xl border border-white/15 bg-black/20 p-4">
              <div className="font-mono text-[11px] tracking-wider text-slate-400">&gt; INQUIRY DIRECTIVE</div>
              <textarea className="mt-2 h-24 w-full resize-none bg-transparent font-mono text-[17px] leading-snug text-white outline-none" value={form.question} onChange={(e) => set({ question: e.target.value })} />
            </div>
            <div className="rounded-xl border border-white/15 bg-black/20 p-3">
              <div className="font-mono text-[11px] tracking-wider text-slate-300">TELEMETRY ANOMALIES</div>
              <ProgressionChart data={series} height={100} axis />
              <div className="flex justify-between font-mono text-[9px] text-slate-500"><span>24h ago</span><span>now</span></div>
            </div>
          </div>
          <div className="mt-3 flex items-center justify-between font-mono text-[11px] tracking-wider text-slate-400"><span><span className="text-cyan-300">QUERY LENGTH:</span> {form.question.length} Characters</span><span>| DUAL-HYPOTHESIS HAZARD DETECTION</span></div>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button onClick={run} disabled={S.running || S.offline} className="inline-flex items-center gap-3 rounded-lg border border-cyan-300/60 bg-cyan-400/15 px-6 py-3 font-mono text-sm tracking-wider text-cyan-100 shadow-[0_0_24px_rgba(34,211,238,0.25)] transition hover:bg-cyan-400/25 disabled:opacity-40">{S.running ? 'INVESTIGATION RUNNING…' : 'START INVESTIGATION'} <span className="text-lg">✻</span></button>
            <div className="flex overflow-hidden rounded-lg border border-white/15 font-mono text-[11px]">
              {Object.entries(TIERS).map(([k, t]) => <button key={k} title={t.sources.map((s) => SRC_LABEL[s]).join(' · ')} onClick={() => set({ tier: +k })} className={`px-3 py-2 ${form.tier === +k ? 'bg-cyan-400/20 text-cyan-200' : 'text-slate-400 hover:bg-white/5'}`}>TIER {k} · {t.label.toUpperCase()}</button>)}
            </div>
            <div className="flex flex-wrap gap-2">
              {Object.entries(PRESETS).map(([k, p]) => <button key={k} className="rounded-md border border-white/15 px-2.5 py-1.5 text-[11px] text-slate-300 hover:border-white/40" onClick={() => set({ location: p.location, country: p.country, tier: p.tier, question: p.question })}>{p.label}</button>)}
            </div>
          </div>
        </section>

        <section className="card p-5">
          <div className="flex items-center justify-between"><h3 className="font-mono text-[12px] tracking-[0.18em] text-cyan-300">GEOSPATIAL TARGET &amp; TELEMETRY</h3><span className={`font-mono text-[11px] ${S.health ? 'text-emerald-400' : 'text-red-400'}`}>RADAR LOCK: {S.health ? 'ACTIVE' : 'OFFLINE'}</span></div>
          <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label="Centroid latitude" value={lat$(d.target?.lat)} /><Stat label="Centroid longitude" value={lon$(d.target?.lon)} /><Stat label="Urban footprint" value="N/A" /><Stat label="Density index" value="N/A" />
          </div>
          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-[2fr_1fr]">
            <div><label className="label">Target location</label><input className="input mt-1" value={form.location} onChange={(e) => set({ location: e.target.value })} /></div>
            <div><label className="label">Country hint (optional)</label><input className="input mt-1" value={form.country} onChange={(e) => set({ country: e.target.value })} /></div>
          </div>
        </section>
      </div>

      <div className="space-y-5 pt-2">
        <section className="card overflow-hidden">
          <div className={`bg-gradient-to-b to-transparent p-4 ${HEAD[level]}`}>
            <h2 className="text-xl font-bold uppercase leading-tight"><span className="text-slate-300">SITUATION:</span> <span className="text-red-300">{headline}</span></h2>
            <div className="mt-2 font-mono text-[11px] text-slate-300">{gmtStamp(feed?.generated_at)}</div>
          </div>
          <div className="p-4">
            <h3 className="text-[17px] font-semibold text-white">Anomalies per Sector</h3>
            <SectorChart rows={sectors} />
            <div className="mt-1 flex justify-end gap-3 font-mono text-[10px] text-slate-400"><span className="text-red-400">■ Events</span><span className="text-amber-400">■ High severity</span></div>
          </div>
        </section>

        <section className="card p-4">
          <h3 className="text-[13px] uppercase tracking-[0.18em] text-slate-400">Recent sector events</h3>
          <ul className="mt-2 space-y-2.5">
            {events.slice(0, 3).map((e) => (
              <li key={e.id} className="flex items-center gap-3"><span className={`h-4 w-4 shrink-0 rounded-full border-2 ${RING[e.level]}`} /><span className="min-w-0 flex-1 truncate text-[15px] text-white">{e.place}</span><span className={`font-mono text-[12px] ${e.level === 'LOW' ? 'text-emerald-400' : 'text-amber-300'}`}>{clock(e.time)}</span></li>
            ))}
            {!feed && <li className="text-sm text-slate-500">—</li>}
          </ul>
        </section>

        <section className="card p-4">
          <h3 className="text-[13px] uppercase tracking-[0.18em] text-slate-400">Selected anomaly</h3>
          <div className="mt-1 flex items-start gap-3"><span className="font-mono text-4xl font-bold text-amber-300">{strongest ? `M${num(strongest.magnitude, 1)}` : '—'}</span><span className="pt-1 text-[11px] font-semibold uppercase leading-tight text-white">STRONGEST EVENT<br />IN LAST 24 H</span></div>
          <p className="mt-1 text-xs leading-snug text-slate-400">{strongest ? `${strongest.place} · depth ${num(strongest.depth_km, 0)} km` : ''}</p>
          <h4 className="mt-3 text-[15px] font-semibold text-white">Anomaly Progression</h4>
          <ProgressionChart data={series} height={90} />
        </section>
      </div>
    </div>
  );
}
