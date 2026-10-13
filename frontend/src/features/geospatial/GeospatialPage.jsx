import { Circle, CircleMarker, MapContainer, Polyline, TileLayer, Tooltip, useMap } from 'react-leaflet';
import { useEffect } from 'react';
import { Empty, PageHeader, Panel, Stat } from '../../shared/components/ui';
import { useInvestigation } from '../../store/InvestigationContext';
import { destination } from '../../core/utils/geo';
import { lat$, lon$, num } from '../../core/utils/format';

function Center({ at }) { const m = useMap(); useEffect(() => { m.setView(at, 8); }, [at, m]); return null; }

// In other words: shows the target, the fire hotspots around it, the radius searched and the wind direction.
export default function GeospatialPage() {
  const { d } = useInvestigation();
  if (!d.target) return <><PageHeader kicker="GIS DOCK" stage="05" title="Geospatial Plume Theater" /><Empty /></>;
  const at = [d.target.lat, d.target.lon];
  const fires = d.ev.fire?.observations || [];
  const places = d.ev.geo?.observations || [];
  const windFrom = d.sig.wind_direction_deg; // wind blows FROM this bearing → smoke travels the opposite way
  const plumeEnd = windFrom != null ? destination(at[0], at[1], (windFrom + 180) % 360, 40) : null;
  const windStart = windFrom != null ? destination(at[0], at[1], windFrom, 40) : null;
  return (
    <div className="space-y-4">
      <PageHeader kicker={`${d.target.name.toUpperCase()} GIS DOCK // ${lat$(d.target.lat)} ${lon$(d.target.lon)}`} stage="05" title="Geospatial Plume Theater" />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_300px]">
        <div className="panel h-[560px] overflow-hidden p-0">
          <MapContainer center={at} zoom={8} style={{ height: '100%' }}>
            <TileLayer attribution="Esri World Imagery" url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" />
            <Center at={at} />
            {d.ev.fire?.measurements?.radius_km && <Circle center={at} radius={d.ev.fire.measurements.radius_km * 1000} pathOptions={{ color: '#22d3ee', weight: 1, dashArray: '6 6', fillOpacity: 0.03 }} />}
            {windStart && <Polyline positions={[windStart, at, plumeEnd]} pathOptions={{ color: '#a78bfa', weight: 3, dashArray: '2 8' }}><Tooltip sticky>Wind from {num(windFrom, 0)}°</Tooltip></Polyline>}
            <CircleMarker center={at} radius={9} pathOptions={{ color: '#22d3ee', fillColor: '#22d3ee', fillOpacity: 0.6 }}><Tooltip permanent direction="top">{d.target.name}</Tooltip></CircleMarker>
            {fires.map((f, i) => <CircleMarker key={i} center={[f.lat, f.lon]} radius={4 + (f.frp_mw || 0) / 12} pathOptions={{ color: '#fb923c', fillColor: '#fb923c', fillOpacity: 0.5 }}><Tooltip>FRP {num(f.frp_mw, 1)} MW · {num(f.distance_km, 0)} km</Tooltip></CircleMarker>)}
            {places.map((p, i) => <CircleMarker key={`p${i}`} center={[p.lat, p.lon]} radius={4} pathOptions={{ color: '#34d399', fillOpacity: 0.7 }}><Tooltip>{p.name}</Tooltip></CircleMarker>)}
          </MapContainer>
        </div>
        <div className="space-y-3">
          <Stat label="Hotspots in radius" value={d.sig.fire_count ?? 0} />
          <Stat label="Nearest hotspot" value={num(d.sig.nearest_fire_km, 0)} unit={`km ${d.dirLabel}`} />
          <Stat label="Wind from" value={num(windFrom, 0)} unit="°" />
          <Stat label="Downwind of fire" value={d.sig.is_downwind_of_fire ? 'YES' : 'NO'} level={d.sig.is_downwind_of_fire ? 'HIGH' : 'LOW'} />
          <Panel title="Legend"><ul className="space-y-1 text-xs text-slate-400"><li><span className="text-accent">●</span> Target</li><li><span className="text-orange-400">●</span> Fire hotspot (size = FRP)</li><li><span className="text-emerald-400">●</span> Infrastructure</li><li><span className="text-violet-400">┄</span> Wind axis</li></ul></Panel>
        </div>
      </div>
    </div>
  );
}
