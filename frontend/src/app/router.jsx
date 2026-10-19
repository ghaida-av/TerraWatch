import { Suspense, lazy } from 'react';
import { Link, Navigate, Route, Routes } from 'react-router-dom';
import AppShell from '../shared/layout/AppShell';
import ErrorBoundary from '../shared/components/ErrorBoundary';

// In other words: each screen loads on demand, so the first page doesn't download Recharts + Leaflet for everything.
const MonitorPage = lazy(() => import('../features/monitor/MonitorPage'));
const DispatchPage = lazy(() => import('../features/dispatch/DispatchPage'));
const HudPage = lazy(() => import('../features/hud/HudPage'));
const RiskPage = lazy(() => import('../features/risk/RiskPage'));
const EvidencePage = lazy(() => import('../features/evidence/EvidencePage'));
const GeospatialPage = lazy(() => import('../features/geospatial/GeospatialPage'));
const SitrepPage = lazy(() => import('../features/sitrep/SitrepPage'));
const SourcesPage = lazy(() => import('../features/sources/SourcesPage'));

const NotFound = () => (
  <div className="card m-6 max-w-md p-6">
    <h1 className="text-2xl font-semibold text-white">Page not found</h1>
    <p className="mt-2 text-sm text-slate-400">That screen doesn't exist.</p>
    <Link to="/monitor" className="btn-solid mt-4">Back to Earth Monitor</Link>
  </div>
);

// The monitor is full-screen (no <main> wrapper in AppShell), so it gets its own Suspense + boundary here.
const MonitorRoute = () => (
  <ErrorBoundary><Suspense fallback={<div role="status" className="absolute inset-0 grid place-items-center font-mono text-xs tracking-wider text-slate-400">LOADING MONITOR…</div>}><MonitorPage /></Suspense></ErrorBoundary>
);

export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/monitor" replace />} />
        <Route path="/monitor" element={<MonitorRoute />} />
        <Route path="/dispatch" element={<DispatchPage />} />
        <Route path="/hud" element={<HudPage />} />
        <Route path="/risk" element={<RiskPage />} />
        <Route path="/evidence" element={<EvidencePage />} />
        <Route path="/geospatial" element={<GeospatialPage />} />
        <Route path="/sitrep" element={<SitrepPage />} />
        <Route path="/sources" element={<SourcesPage />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
