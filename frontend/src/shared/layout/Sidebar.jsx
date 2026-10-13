import { NavLink } from 'react-router-dom';
import { NAV } from './nav';
import { useInvestigation } from '../../store/InvestigationContext';
import { useGlobalEvents } from '../../features/monitor/useGlobalEvents';
import { levelStyle } from '../../core/utils/risk';

export default function Sidebar() {
  const { S, d } = useInvestigation();
  const { data } = useGlobalEvents({ window: 'day', minMag: 2.5 });
  const alerts = data ? data.summary.levels.HIGH + data.summary.levels.CRITICAL : 0;

  // In other words: the little line under each title changes with real state (running, alerts, risk level…).
  const sub = (n) => {
    if (n.path === '/monitor') return data ? [alerts ? `ACTIVE - ${alerts} ALERTS` : 'ACTIVE - NO THREATS', alerts ? 'text-amber-300' : 'text-emerald-400'] : ['CONNECTING…', 'text-slate-500'];
    if (n.path === '/hud') return [S.running ? 'STREAMING' : d.r ? 'COMPLETE' : 'IDLE - WAITING', S.running ? 'text-cyan-300' : 'text-slate-500'];
    if (n.path === '/risk' && d.r) return [`${d.r.risk_level} · ${d.r.risk_score.toFixed(2)}`, levelStyle(d.r.risk_level).text];
    if (n.path === '/sources') return [`${S.sources?.total_sources ?? 0} APIS`, 'text-slate-500'];
    return [n.sub, 'text-slate-500'];
  };
  const right = (n) => {
    if (n.path === '/monitor' && data) return <span className="text-right"><span className="flex items-center justify-end gap-1.5 font-mono text-base text-emerald-400"><span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />{data.total}</span><span className="block text-[9px] tracking-widest text-slate-500">LIVE EVENTS</span></span>;
    if (n.path === '/hud') return <span className={`h-2.5 w-2.5 rounded-full ${S.running ? 'animate-pulse bg-cyan-400' : 'bg-slate-500'}`} />;
    if (n.path === '/risk') return <span className="grid h-5 w-5 place-items-center rounded border border-slate-600 text-xs text-slate-400">−</span>;
    if (n.tag) return <span className="font-mono text-[10px] tracking-wider text-cyan-300/80">{n.tag}</span>;
    return null;
  };

  return (
    <aside className="glass !bg-[#0a1020]/95 absolute bottom-4 left-4 top-4 z-30 flex w-[19rem] flex-col overflow-hidden">
      <div className={`flex items-center gap-2 border-b border-white/10 px-4 py-2.5 font-mono text-[11px] tracking-wider ${S.offline ? 'bg-red-500/10 text-red-300' : 'bg-emerald-500/10 text-emerald-300'}`}>
        <span>((•))</span><span>NETWORK STATUS:</span><span className="flex items-center gap-1"><span className={`h-1.5 w-1.5 rounded-full ${S.offline ? 'bg-red-400' : 'bg-emerald-400'}`} />{S.offline ? 'OFFLINE' : 'OPTIMAL'}</span>
      </div>
      <div className="px-4 pb-1 pt-4 text-[11px] uppercase tracking-[0.2em] text-slate-500">Observatory control</div>
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 pb-2">
        {NAV.map((n) => { const [s, c] = sub(n); return (
          <NavLink key={n.path} to={n.path} className={({ isActive }) => `flex items-center gap-3 rounded-lg border-l-2 px-3 py-2.5 transition ${isActive ? 'border-violet-400 bg-violet-500/15 text-white' : 'border-transparent text-slate-300 hover:bg-white/5'}`}>
            <span className="w-5 font-mono text-xs text-slate-500">{n.id}</span>
            <span className="min-w-0 flex-1 leading-tight"><span className="block truncate text-[15px]">{n.title}</span><span className={`block text-[10px] uppercase tracking-wider ${c}`}>{s}</span></span>
            {right(n)}
          </NavLink>); })}
      </nav>
      <div className="m-3 rounded-xl border border-white/10 bg-black/20 p-3">
        <div className="flex justify-between text-[11px] tracking-[0.18em] text-slate-400"><span>PIPELINE HEALTH</span><span className={S.health ? 'text-emerald-400' : 'text-red-400'}>{S.health ? 'OPTIMAL' : 'OFFLINE'}</span></div>
        <div className="mt-2 h-1.5 overflow-hidden rounded bg-slate-800"><div className={`h-full rounded ${S.health ? 'w-full bg-emerald-400' : 'w-1/6 bg-red-500'}`} /></div>
        <div className="mt-2 flex justify-between font-mono text-[10px] text-slate-500"><span>LATENCY: {S.rtt ?? '–'}ms</span><span>QUORUM: {d.queried ? `${d.okCount}/${d.queried}` : '–'}</span></div>
      </div>
    </aside>
  );
}
