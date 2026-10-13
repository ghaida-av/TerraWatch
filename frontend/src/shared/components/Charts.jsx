import { Area, AreaChart, Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

const tip = { background: '#0b1220', border: '1px solid #1b2a42', fontSize: 11 };

// Orange/cyan glowing line like the "Anomaly progression" mini charts.
export function ProgressionChart({ data, height = 70, axis = false }) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ top: 4, right: 2, left: axis ? -22 : 0, bottom: 0 }}>
          <defs><linearGradient id="pg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#fb923c" stopOpacity=".45" /><stop offset="100%" stopColor="#22d3ee" stopOpacity="0" /></linearGradient></defs>
          {axis && <XAxis dataKey="i" hide />}{axis && <YAxis tick={{ fill: '#64748b', fontSize: 9 }} axisLine={false} tickLine={false} allowDecimals={false} />}
          <Tooltip contentStyle={tip} labelFormatter={() => ''} formatter={(v) => [`${v} events`, '']} />
          <Area type="monotone" dataKey="n" stroke="#22d3ee" strokeWidth={1.6} fill="url(#pg)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// "Anomalies per sector": red bars, amber where high-severity events exist.
export function SectorChart({ rows, height = 150 }) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ top: 4, right: 4, left: -22, bottom: 0 }}>
          <XAxis dataKey="k" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: '#64748b', fontSize: 9 }} axisLine={{ stroke: '#1b2a42' }} tickLine={false} allowDecimals={false} />
          <Tooltip cursor={{ fill: 'rgba(255,255,255,.04)' }} contentStyle={tip} formatter={(v) => [`${v} events`, '']} labelFormatter={(k) => `Sector ${k}`} />
          <Bar dataKey="n" radius={[2, 2, 0, 0]}>{rows.map((r) => <Cell key={r.k} fill={r.high ? '#f59e0b' : '#ef4444'} />)}</Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
