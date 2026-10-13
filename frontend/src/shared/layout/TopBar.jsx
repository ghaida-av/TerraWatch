import { NavLink, useNavigate } from 'react-router-dom';

const TABS = [
  { to: '/monitor', label: 'Earth Monitor' },
  { to: '/risk', label: 'Analysis Lab' },
  { to: '/dispatch', label: 'Investigations' },
];

export default function TopBar({ overlay = false }) {
  const go = useNavigate();
  return (
    <header className={`${overlay ? 'monitor-topbar absolute inset-x-0 top-0 z-[1100]' : 'relative z-40'} flex items-center justify-between gap-4 px-5 py-3`}>
      <div className="flex items-center gap-3">
        <div className="grid h-11 w-11 place-items-center rounded-xl border border-white/15 bg-white/5 text-cyan-300">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="9" /><path d="M5 12h4l2-5 3 10 2-5h3" strokeLinecap="round" strokeLinejoin="round" /></svg>
        </div>
        <span className="text-lg font-bold tracking-[0.12em] text-white">TERRAWATCH</span>
        <span className="rounded border border-teal-400/50 bg-teal-400/10 px-2 py-1 font-mono text-[10px] tracking-widest text-teal-200">EARTH OBSERVATORY</span>
      </div>
      <nav className="hidden gap-3 md:flex">
        {TABS.map((t) => (
          <NavLink key={t.to} to={t.to} className={({ isActive }) => `rounded-lg border px-5 py-2 text-[15px] transition ${isActive ? 'border-violet-400/60 bg-violet-500/40 text-white' : 'border-white/15 bg-white/5 text-slate-300 hover:text-white'}`}>{t.label}</NavLink>
        ))}
      </nav>
      <div className="flex items-center gap-3">
        <button className="btn-solid" onClick={() => go('/dispatch')}>✻ Run investigation</button>
        <span className="grid h-9 w-9 place-items-center rounded-lg border border-cyan-400/40 bg-cyan-400/10 font-mono text-xs text-cyan-200">OP</span>
        <NavLink to="/sitrep" className={({ isActive }) => `hidden rounded-lg border px-5 py-2 text-[15px] lg:block ${isActive ? 'border-violet-400/60 bg-violet-500/40 text-white' : 'border-white/15 bg-white/5 text-slate-300 hover:text-white'}`}>Situation Report</NavLink>
      </div>
    </header>
  );
}
