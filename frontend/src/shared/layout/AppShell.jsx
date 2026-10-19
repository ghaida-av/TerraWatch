import { Suspense, useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import TopBar from './TopBar';
import Sidebar from './Sidebar';
import BackdropMap from './BackdropMap';
import ErrorBoundary from '../components/ErrorBoundary';
import { useInvestigation } from '../../store/InvestigationContext';

const Loading = () => <div role="status" className="p-8 font-mono text-xs tracking-wider text-slate-400">LOADING…</div>;

// In other words: glowing gradient frame -> top bar -> a stage where the sidebar FLOATS over the page/map.
// On wide screens the sidebar is docked; on narrow screens (and on the full-screen monitor) it is a drawer
// opened from the top bar's menu button.
export default function AppShell() {
  const { S } = useInvestigation();
  const { pathname } = useLocation();
  const full = pathname === '/monitor'; // the monitor is a full-screen map with floating panels
  const [menu, setMenu] = useState(false);
  useEffect(() => { setMenu(false); }, [pathname]);
  useEffect(() => {
    if (!menu) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') setMenu(false); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [menu]);

  return (
    <div className={`h-full ${full ? 'p-0' : 'p-1.5'}`}>
      <div className={`h-full ${full ? 'bg-[#071019]' : 'rounded-2xl bg-gradient-to-br from-cyan-400/70 via-violet-500/60 to-pink-400/70 p-[2px]'}`}>
        <div className={`relative flex h-full flex-col overflow-hidden bg-void ${full ? '' : 'rounded-[14px]'}`}>
          <TopBar overlay={full} menuOpen={menu} onMenu={() => setMenu((m) => !m)} />
          {S.offline && (
            <div role="alert" className="relative z-40 border-y border-red-500/30 bg-red-500/10 px-5 py-1.5 font-mono text-xs text-red-300">
              Cannot reach the TerraWatch API. From the repo root run: <b>TERRAWATCH_MODE=live python -m uvicorn apps.api.main:app --reload --port 8000</b>
            </div>
          )}
          <div className="relative min-h-0 flex-1">
            {!full && <BackdropMap />}
            {(menu) && <button aria-label="Close navigation" tabIndex={-1} onClick={() => setMenu(false)} className={`absolute inset-0 bg-black/50 ${full ? 'z-[1150]' : 'z-20 lg:hidden'}`} />}
            <Sidebar open={menu} docked={!full} overlay={full} onClose={() => setMenu(false)} />
            {full ? <Outlet /> : (
              <main className="absolute inset-0 overflow-y-auto py-2 pl-4 pr-4 lg:pl-[20.5rem] lg:pr-5">
                <ErrorBoundary resetKey={pathname}><Suspense fallback={<Loading />}><Outlet /></Suspense></ErrorBoundary>
              </main>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
