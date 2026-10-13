// In other words: draws the backend's evidence graph (nodes + links) as a simple SVG, no graph library needed.
const COLORS = { target: '#22d3ee', fire: '#fb923c', wind: '#a78bfa', air_quality: '#34d399', weather: '#a78bfa', earthquake: '#fbbf24' };

export default function GraphView({ graph, selected, onSelect }) {
  const nodes = graph?.nodes || [], links = graph?.relationships || [];
  if (!nodes.length) return null;
  const W = 640, H = 340, cx = W / 2, cy = H / 2;
  const target = nodes.find((n) => n.type === 'target') || nodes[0];
  const others = nodes.filter((n) => n.id !== target.id);
  const pos = { [target.id]: [cx, cy] };
  others.forEach((n, i) => { const a = (i / Math.max(others.length, 1)) * Math.PI * 2 - Math.PI / 2; pos[n.id] = [cx + Math.cos(a) * 230, cy + Math.sin(a) * 125]; });
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
      <defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10z" fill="#475569" /></marker></defs>
      {links.map((l, i) => { const a = pos[l.source], b = pos[l.target]; if (!a || !b) return null;
        return <g key={i}><line x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} stroke="#334155" strokeWidth="1.5" markerEnd="url(#arr)" /><text x={(a[0] + b[0]) / 2} y={(a[1] + b[1]) / 2 - 4} fill="#64748b" fontSize="9" textAnchor="middle" fontFamily="monospace">{l.type}</text></g>; })}
      {nodes.map((n) => { const [x, y] = pos[n.id] || [cx, cy], on = selected?.id === n.id, col = COLORS[n.type] || '#94a3b8';
        return (
          <g key={n.id} onClick={() => onSelect?.(n)} style={{ cursor: 'pointer' }}>
            <circle cx={x} cy={y} r={on ? 20 : 16} fill={col} fillOpacity="0.18" stroke={col} strokeWidth={on ? 3 : 1.5} />
            <text x={x} y={y + 34} fill="#cbd5e1" fontSize="10" textAnchor="middle" fontFamily="monospace">{n.id.length > 18 ? `${n.id.slice(0, 17)}…` : n.id}</text>
          </g>
        ); })}
    </svg>
  );
}
