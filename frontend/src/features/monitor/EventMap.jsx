import { useEffect } from 'react';
import { CircleMarker, MapContainer, TileLayer, useMap } from 'react-leaflet';

// Ring colours follow the design: green = nominal, yellow/orange = alert, red = critical.
const RING = { LOW: '#4ade80', MODERATE: '#fde047', HIGH: '#fb923c', CRITICAL: '#f87171' };

function Fly({ target, nonce }) {
  const map = useMap();
  useEffect(() => { if (target) map.flyTo([target.lat, target.lon], Math.max(map.getZoom(), 4), { duration: 0.9 }); }, [target, nonce, map]);
  return null;
}

// In other words: zoom + / − / "locate" buttons in a dark pill, like the design.
function ZoomPad({ home }) {
  const map = useMap();
  const b = 'grid h-10 w-10 place-items-center text-lg text-slate-200 hover:bg-white/10';
  return (
    <div className="monitor-zoom absolute bottom-24 left-1/2 z-[1000] flex -translate-x-1/2 overflow-hidden rounded-xl border border-white/15 bg-[#0a1020]/90 backdrop-blur" onDoubleClick={(e) => e.stopPropagation()}>
      <button className={b} onClick={() => map.zoomIn()}>+</button>
      <button className={`${b} border-x border-white/10`} onClick={() => map.zoomOut()}>−</button>
      <button className={b} onClick={() => map.flyTo(home, 4)}>◎</button>
    </div>
  );
}

// Full-screen satellite map. Each event = two hollow concentric rings (outer + inner), like the design.
export default function EventMap({ events, selected, nonce, onSelect }) {
  const home = [10, 115];
  return (
    <MapContainer center={home} zoom={3} minZoom={2} worldCopyJump zoomControl={false} style={{ height: '100%', width: '100%' }}>
      <TileLayer attribution="Esri World Imagery" url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" />
      {events.map((e) => {
        const c = RING[e.level] || '#fff', r = 6 + (e.magnitude || 0) * 2.4, on = selected?.id === e.id, click = { click: () => onSelect?.(e) };
        return (
          <span key={e.id}>
            <CircleMarker center={[e.lat, e.lon]} radius={r + 7} pathOptions={{ color: c, weight: on ? 3 : 2, opacity: on ? 1 : 0.85, fillOpacity: 0 }} eventHandlers={click} />
            <CircleMarker center={[e.lat, e.lon]} radius={r} pathOptions={{ color: c, weight: 2.5, fillColor: '#050810', fillOpacity: 0.55 }} eventHandlers={click} />
            <CircleMarker center={[e.lat, e.lon]} radius={2.5} pathOptions={{ color: c, weight: 1, fillColor: c, fillOpacity: 1 }} eventHandlers={click} />
          </span>
        );
      })}
      <Fly target={selected} nonce={nonce} />
      <ZoomPad home={home} />
    </MapContainer>
  );
}
