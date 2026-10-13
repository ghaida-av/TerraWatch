import { compass } from '../../core/utils/geo';
import { num } from '../../core/utils/format';

// In other words: the 3 text lines each source card shows, built from the real evidence numbers.
export function hudLines(src, ev, d, asked, running) {
  if (!ev) return asked && running ? ['Collecting evidence…', 'Waiting for the adapter', ''] : ['Not requested', 'Choose a deeper tier to include it', ''];
  const m = ev.measurements || {};
  if (ev.status !== 'ok') return ['Source error', ev.error?.message || ev.error || 'Upstream unavailable', ''];
  if (src === 'air_quality') return ['PM2.5 at nearest station', `${num(m.pm25, 0)} µg/m³ (${num(d.sig.pm25_anomaly_ratio, 2)}× 24 h baseline)`, `${m.station?.name || '—'} · ${num(m.station?.distance_km, 1)} km`];
  if (src === 'fire') return ['Nearest thermal hotspot', `${num(m.nearest_km, 0)} km ${d.dirLabel}`, `${num(m.max_frp_mw, 1)} MW peak FRP · ${m.hotspot_count} hotspots`];
  if (src === 'weather') { const c = m.current || {}; return ['Surface wind', `${num(c.wind_speed_kmh, 0)} km/h from ${num(c.wind_direction_deg, 0)}° (${compass(c.wind_direction_deg)})`, `${num(c.temperature_c, 1)} °C · RH ${num(c.relative_humidity_pct, 0)}%`]; }
  if (src === 'earthquake') return [`Seismic events (${m.window_days} d)`, m.event_count ? `M${num(m.max_magnitude, 1)} max · ${m.event_count} events` : 'No events', m.nearest_km != null ? `nearest ${num(m.nearest_km, 0)} km` : ''];
  return ['Nearby infrastructure', `${m.feature_count} features within ${num(m.radius_m / 1000, 0)} km`, Object.entries(m.by_category || {}).slice(0, 2).map(([k, v]) => `${k.split('.').pop()} ×${v}`).join(' · ')];
}
