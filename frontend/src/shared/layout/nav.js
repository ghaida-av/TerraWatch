// In other words: the single list that builds the sidebar. Add a page = add one line here (+ a Route).
// tag: small label on the right of the item (like INPUT / DAG / GIS in the design)
export const NAV = [
  { id: '00', path: '/monitor',    title: 'Global Event Monitor',     sub: 'LIVE EARTH FEED' },
  { id: '01', path: '/dispatch',   title: 'Investigation Dispatch',   sub: 'CONFIGURE QUERY', tag: 'INPUT' },
  { id: '02', path: '/hud',        title: 'Live Investigation HUD',   sub: 'IDLE - WAITING' },
  { id: '03', path: '/risk',       title: 'Risk Overview',            sub: 'PERFORMANCE METRICS' },
  { id: '04', path: '/evidence',   title: 'Evidence & Causal Graph',  sub: 'ANALYZE FEEDS', tag: 'DAG' },
  { id: '05', path: '/geospatial', title: 'Geospatial Plume Theater', sub: 'MANAGE LAYERS', tag: 'GIS' },
  { id: '06', path: '/sitrep',     title: 'Situation Report',         sub: 'GENERATE REPORTS' },
  { id: '07', path: '/sources',    title: 'Data Sources & Feeds',     sub: 'ACCESS LOGS' },
];
