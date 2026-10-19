// In other words: a cheap, static "dim planet" backdrop behind the pages. It used to start a whole Leaflet map
// (and download satellite tiles) on every screen; gradients look nearly the same and cost nothing.
export default function BackdropMap() {
  return (
    <div aria-hidden="true" className="backdrop-map pointer-events-none absolute inset-0 overflow-hidden">
      <div className="absolute inset-0" style={{ background: 'radial-gradient(900px 520px at 78% 18%, rgba(34,211,238,.10), transparent 70%), radial-gradient(800px 520px at 12% 92%, rgba(139,92,246,.12), transparent 70%)' }} />
      <div className="absolute inset-0 opacity-[0.07]" style={{ backgroundImage: 'linear-gradient(#7dd3fc 1px, transparent 1px), linear-gradient(90deg, #7dd3fc 1px, transparent 1px)', backgroundSize: '56px 56px' }} />
      <div className="absolute inset-0 bg-gradient-to-b from-void/60 via-transparent to-void/80" />
    </div>
  );
}
