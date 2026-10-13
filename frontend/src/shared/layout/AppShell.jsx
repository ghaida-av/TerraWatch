import { Outlet, useLocation } from 'react-router-dom';
import TopBar from './TopBar';
import Sidebar from './Sidebar';
import BackdropMap from './BackdropMap';
import { useInvestigation } from '../../store/InvestigationContext';

// In other words: glowing gradient frame -> top bar -> a stage where the sidebar FLOATS over the page/map.
export default function AppShell() {
  const { S } = useInvestigation();
  const full = useLocation().pathname === '/monitor'; // the monitor is a full-screen map with floating panels
  return (
    <div className={`h-full ${full ? 'p-0' : 'p-1.5'}`}>
      <div className={`h-full ${full ? 'bg-[#071019]' : 'rounded-2xl bg-gradient-to-br from-cyan-400/70 via-violet-500/60 to-pink-400/70 p-[2px]'}`}>
        <div className={`relative flex h-full flex-col overflow-hidden bg-void ${full ? '' : 'rounded-[14px]'}`}>
          <TopBar overlay={full} />
          {S.offline && (
            <div className="relative z-40 border-y border-red-500/30 bg-red-500/10 px-5 py-1.5 font-mono text-xs text-red-300">
              Cannot reach the TerraWatch API. Start it: <b>cd backend &amp;&amp; TERRAWATCH_MODE=mock python -m uvicorn apps.api.main:app --port 8001</b>
            </div>
          )}
          <div className="relative min-h-0 flex-1">
            {!full && <BackdropMap />}
            {!full && <Sidebar />}
            {full ? <Outlet /> : (
              <main className="absolute inset-0 overflow-y-auto py-2 pl-[20.5rem] pr-5"><Outlet /></main>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
