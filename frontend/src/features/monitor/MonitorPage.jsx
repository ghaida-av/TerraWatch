import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import EventMap from './EventMap';
import CountryFlag from './CountryFlag';
import { useGlobalEvents } from './useGlobalEvents';
import { ProgressionChart } from '../../shared/components/Charts';
import { ago, num } from '../../core/utils/format';
import { clock, gmtStamp, progression, STATUS, topLevel } from '../../core/utils/events';

const FILTERS = [['ALL', 0], ['M4+', 4], ['M5+', 5], ['M6+', 6]];
const RING_BORDER = { LOW: 'border-emerald-400', MODERATE: 'border-yellow-300', HIGH: 'border-orange-400', CRITICAL: 'border-red-400' };
const coord = (v, p, n) => `${num(Math.abs(v), 3)}° ${v >= 0 ? p : n}`;

export default function MonitorPage() {
  const [win, setWin] = useState('day');
  const [min, setMin] = useState(0);
  const [sel, setSel] = useState(null);
  const [nonce, setNonce] = useState(0);
  const go = useNavigate();
  const { data, error } = useGlobalEvents({ window: win, minMag: 2.5 });

  const events = useMemo(() => (data?.events || []).filter((e) => (e.magnitude || 0) >= min), [data, min]);
  const top = topLevel(data?.summary?.levels);
  const strongest = useMemo(() => [...(data?.events || [])].sort((a, b) => (b.magnitude || 0) - (a.magnitude || 0))[0], [data]);
  const shown = sel || strongest;
  const series = useMemo(() => progression(data?.events || [], win), [data, win]);
  const alerts = data ? data.summary.levels.HIGH + data.summary.levels.CRITICAL : 0;
  const liveFeed = data?.mode === 'live' && data.source_status === 'ok';
  const feedLabel = liveFeed ? 'USGS LIVE' : data?.mode === 'mock' ? 'SYNTHETIC DEMO' : data?.mode?.toUpperCase() || 'CONNECTING';

  return (
    <div className="monitor-page absolute inset-0">
      <EventMap events={events} selected={sel} nonce={nonce} onSelect={setSel} />

      <div className="monitor-map-label pointer-events-none absolute left-5 top-[5.25rem] z-[500] flex items-center gap-3 font-mono text-[11px] tracking-wider text-slate-200">
        <span className={`monitor-live-dot h-2 w-2 rounded-full ${liveFeed ? 'bg-emerald-400' : 'bg-amber-400'}`} />PLANETARY SEISMIC NETWORK<span className="text-slate-500">|</span><span className="text-slate-400">{feedLabel}</span>
      </div>

      {/* right floating panel */}
      <aside className="monitor-rail glass absolute bottom-20 right-4 top-16 z-[600] w-[23.5rem] overflow-y-auto p-5">
        <div className="monitor-rail-toolbar flex items-center justify-between gap-2 border-b border-white/10 pb-3 font-mono text-[10px] uppercase tracking-wider text-slate-400">
          <span><span className="text-amber-300">⌂</span> Earth Monitor <span className="px-1 text-slate-600">|</span> {feedLabel}</span>
          <a className={`monitor-online ${liveFeed ? '' : 'monitor-feed-not-live'}`} href="https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson" target="_blank" rel="noreferrer"><span className={`h-1.5 w-1.5 rounded-full ${liveFeed ? 'bg-emerald-400' : 'bg-amber-400'}`} /> USGS SOURCE ↗</a>
        </div>
        <div className="mt-4 text-[11px] uppercase tracking-[0.18em] text-slate-400">Current situation: <b className="text-white">{top ? `${top} EVENT` : '—'}</b></div>
        <h2 className="mt-2 text-2xl font-bold uppercase leading-tight text-white">{strongest ? `M${num(strongest.magnitude, 1)} · ${strongest.place}` : 'Loading global feed…'}</h2>
        <div className="mt-1 text-[11px] uppercase tracking-wider text-slate-400">{data ? `${data.total} events in last ${win}` : ''}</div>
        <div className="mt-1 font-mono text-[11px] text-slate-500">{gmtStamp(data?.generated_at)}</div>

        <div className="mt-4 grid grid-cols-2 gap-3">
          <div className="rounded-lg border border-red-500/40 bg-red-500/10 p-3"><div className="font-mono text-3xl font-semibold text-red-400">{alerts}</div><div className="mt-1 text-[10px] uppercase tracking-wider text-slate-300">High-severity<br />events</div></div>
          <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3"><div className="font-mono text-3xl font-semibold text-amber-300">{strongest ? `M${num(strongest.magnitude, 1)}` : '—'}</div><div className="mt-1 text-[10px] uppercase tracking-wider text-slate-300">Strongest<br />event</div></div>
        </div>

        <div className="mt-5 flex items-baseline justify-between"><h3 className="text-[12px] uppercase tracking-[0.18em] text-slate-300">Latest earthquakes</h3><span className="text-lg font-semibold text-white">{events.length} <span className="text-xs font-normal text-slate-400">SIGNALS</span></span></div>
        <div className="mt-3 flex flex-wrap gap-2">
          {FILTERS.map(([l, v]) => <button key={l} onClick={() => setMin(v)} className={`rounded-md border px-3 py-1 font-mono text-xs ${min === v ? 'border-white/50 bg-white/15 text-white' : 'border-white/15 text-slate-400'}`}>{l}</button>)}
          <span className="ml-auto flex gap-1">{['hour', 'day', 'week'].map((w) => <button key={w} onClick={() => setWin(w)} className={`rounded-md px-2 py-1 font-mono text-[10px] uppercase ${win === w ? 'bg-cyan-400/20 text-cyan-300' : 'text-slate-500'}`}>{w}</button>)}</span>
        </div>
        <ul className="monitor-event-list mt-2 max-h-40 divide-y divide-white/10 overflow-y-auto">
          {events.map((e) => { const [label, col] = STATUS[e.level]; return (
            <li key={e.id}><button onClick={() => { setSel(e); setNonce((n) => n + 1); }} className={`monitor-event monitor-event--${(e.level || 'low').toLowerCase()} flex w-full items-center gap-3 py-2.5 text-left hover:bg-white/5 ${sel?.id === e.id ? 'bg-white/5' : ''}`}>
              <span className={`h-3.5 w-3.5 shrink-0 rounded-full border-2 ${RING_BORDER[e.level]}`} />
              <span className="min-w-0 flex-1"><span className="block truncate text-[13px] text-slate-100">{e.place}</span><span className="text-[10px] uppercase tracking-wider text-slate-500">{ago(e.time)}</span></span>
              <span className="flex shrink-0 flex-col items-end gap-1"><span className={`text-right font-mono text-[10px] ${col}`}>{label}</span><CountryFlag lat={e.lat} lon={e.lon} /></span>
            </button></li>); })}
          {data && !events.length && <li className="py-6 text-center text-sm text-slate-500">No events at this threshold.</li>}
        </ul>

        {shown && (
          <div className="mt-4 grid grid-cols-[1.25fr_1fr] gap-4 border-t border-white/10 pt-4">
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Selected anomaly</div>
              <div className="mt-1 flex items-start gap-2"><span className="font-mono text-3xl font-semibold text-amber-300">M{num(shown.magnitude, 1)}</span><span className="text-xs leading-snug text-slate-200">{shown.place}</span></div>
              <div className="mt-1 font-mono text-[10px] text-slate-400">{coord(shown.lat, 'N', 'S')} · {coord(shown.lon, 'E', 'W')}<br />DEPTH {num(shown.depth_km, 0)} KM · {clock(shown.time)}</div>
              <button onClick={() => { setSel(shown); setNonce((n) => n + 1); }} className="mt-3 block rounded-md border border-amber-400/60 px-3 py-1.5 font-mono text-[11px] text-amber-300 hover:bg-amber-400/10">FOCUS ON STATION</button>
              <button onClick={() => (shown.url ? window.open(shown.url, '_blank') : go('/dispatch', { state: { location: (shown.place || '').replace(/^.*? of /, '') } }))} className="mt-2 block rounded-md border border-cyan-400/60 px-3 py-1.5 font-mono text-[11px] text-cyan-300 hover:bg-cyan-400/10">{shown.url ? 'VIEW LOGS' : 'INVESTIGATE AREA'}</button>
            </div>
            <div>
              <div className="text-[11px] text-slate-300">Anomaly progression</div>
              <div className="mt-1 rounded-md border border-white/10 bg-black/20 p-1"><ProgressionChart data={series} height={80} /></div>
              <div className="mt-2 font-mono text-[10px] text-slate-400">STATUS<br /><span className="text-emerald-400">● GREEN</span> <span className="text-amber-300">● ACTIVE ALERT</span></div>
            </div>
          </div>
        )}
        {error && <div className="mt-3 rounded border border-red-500/40 bg-red-500/10 p-2 font-mono text-xs text-red-300">Live feed unavailable. No synthetic events are being shown. {error}</div>}
      </aside>

      {/* bottom status bar */}
      <div className="monitor-status glass absolute bottom-4 left-4 right-[24.5rem] z-[600] flex items-center justify-between px-5 py-3 font-mono text-[11px] tracking-wider text-slate-300">
        <span className="flex items-center gap-3"><span className="h-2 w-2 rounded-full bg-violet-400" />EARTHQUAKE · {shown ? `M ${num(shown.magnitude, 1)}   ${coord(shown.lat, 'N', 'S')} · ${coord(shown.lon, 'E', 'W')}` : '—'}</span>
        <span className="text-slate-500">WGS 84 · TERRAIN: ELLIPSOID</span>
      </div>
    </div>
  );
}
