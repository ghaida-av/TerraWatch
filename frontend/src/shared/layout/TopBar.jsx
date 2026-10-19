import { NavLink, useNavigate } from 'react-router-dom';

const TABS = [
  { to: '/monitor', label: 'Earth Monitor' },
  { to: '/risk', label: 'Analysis Lab' },
  { to: '/dispatch', label: 'Investigations' },
];

// In other words: the header. `overlay` = the compact version that floats over the full-screen monitor map.
// The menu button opens the navigation drawer (always on the monitor, below `lg` elsewhere).
export default function TopBar({ overlay = false, menuOpen = false, onMenu }) {
  const go = useNavigate();
  const tab = (active) => `rounded-lg border text-[15px] transition ${overlay ? 'px-3 py-1.5 font-mono text-[11px]' : 'px-5 py-2'} ${active ? 'border-violet-400/60 bg-violet-500/40 text-white' : 'border-white/15 bg-white/5 text-slate-300 hover:text-white'}`;
  return (
    <header className={`${overlay ? 'absolute inset-x-0 top-0 z-[1100] bg-gradient-to-b from-[rgba(3,8,12,.94)] via-[rgba(3,8,12,.62)] to-transparent px-3 py-2 md:px-[18px] md:py-3' : 'relative z-40 px-3 py-3 md:px-5'} flex items-center justify-between gap-3`}>
      <div className="flex min-w-0 items-center gap-2 md:gap-3">
        <button type="button" onClick={onMenu} aria-label="Toggle navigation" aria-expanded={menuOpen} aria-controls="app-sidebar" className={`grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-white/15 bg-white/5 text-slate-200 hover:bg-white/10 ${overlay ? '' : 'lg:hidden'}`}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M4 7h16M4 12h16M4 17h16" /></svg>
        </button>
        <div className={`grid shrink-0 place-items-center border border-white/15 bg-white/5 text-cyan-300 ${overlay ? 'h-9 w-9 rounded-md border-cyan-400/50 bg-[rgba(4,17,25,.78)]' : 'h-11 w-11 rounded-xl'}`}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M5 12h4l2-5 3 10 2-5h3" strokeLinecap="round" strokeLinejoin="round" /></svg>
        </div>
        <span className={`truncate font-bold text-white ${overlay ? 'text-sm tracking-[0.16em]' : 'text-lg tracking-[0.12em]'}`}>TERRAWATCH</span>
        <span className={`hidden rounded border border-teal-400/50 bg-teal-400/10 px-2 py-1 font-mono tracking-widest text-teal-200 sm:inline ${overlay ? 'text-[10px]' : 'text-[10px]'}`}>EARTH OBSERVATORY</span>
      </div>
      <nav aria-label="Primary" className="hidden gap-2 md:flex md:gap-3">
        {TABS.map((t) => (
          <NavLink key={t.to} to={t.to} className={({ isActive }) => tab(isActive)}>{t.label}</NavLink>
        ))}
      </nav>
      <div className="flex shrink-0 items-center gap-2 md:gap-3">
        <button className={`btn-solid ${overlay ? '!rounded !px-3 !py-2 !text-[11px]' : ''}`} onClick={() => go('/dispatch')} aria-label="Run investigation"><span aria-hidden="true">✻</span><span className="hidden sm:inline">Run investigation</span></button>
        <span aria-hidden="true" className={`hidden place-items-center border border-cyan-400/40 bg-cyan-400/10 font-mono text-xs text-cyan-200 sm:grid ${overlay ? 'h-[30px] w-[30px] rounded' : 'h-9 w-9 rounded-lg'}`}>OP</span>
        <NavLink to="/sitrep" className={({ isActive }) => `hidden lg:block ${tab(isActive)}`}>Situation Report</NavLink>
      </div>
    </header>
  );
}
