import { Navigate, Route, Routes } from 'react-router-dom';
import AppShell from '../shared/layout/AppShell';
import MonitorPage from '../features/monitor/MonitorPage';
import DispatchPage from '../features/dispatch/DispatchPage';
import HudPage from '../features/hud/HudPage';
import RiskPage from '../features/risk/RiskPage';
import EvidencePage from '../features/evidence/EvidencePage';
import GeospatialPage from '../features/geospatial/GeospatialPage';
import SitrepPage from '../features/sitrep/SitrepPage';
import SourcesPage from '../features/sources/SourcesPage';

export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/monitor" replace />} />
        <Route path="/monitor" element={<MonitorPage />} />
        <Route path="/dispatch" element={<DispatchPage />} />
        <Route path="/hud" element={<HudPage />} />
        <Route path="/risk" element={<RiskPage />} />
        <Route path="/evidence" element={<EvidencePage />} />
        <Route path="/geospatial" element={<GeospatialPage />} />
        <Route path="/sitrep" element={<SitrepPage />} />
        <Route path="/sources" element={<SourcesPage />} />
      </Route>
    </Routes>
  );
}
