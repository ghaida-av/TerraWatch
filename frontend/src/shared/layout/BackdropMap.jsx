import { MapContainer, TileLayer } from 'react-leaflet';

// In other words: the dim, non-interactive world map behind the pages (like the Launchpad design).
export default function BackdropMap() {
  return (
    <div className="backdrop-map pointer-events-none absolute inset-0 opacity-40">
      <MapContainer center={[22, 30]} zoom={3} zoomControl={false} attributionControl={false} dragging={false} scrollWheelZoom={false} doubleClickZoom={false} keyboard={false} touchZoom={false} style={{ height: '100%', width: '100%' }}>
        <TileLayer url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" />
      </MapContainer>
      <div className="absolute inset-0 bg-gradient-to-b from-void/70 via-void/40 to-void/80" />
    </div>
  );
}
