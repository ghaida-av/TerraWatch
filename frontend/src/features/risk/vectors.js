import { compass } from '../../core/utils/geo';
import { DASH, num } from '../../core/utils/format';
import { levelOf } from '../../core/utils/risk';

// In other words: builds the 4 hazard cards (air, fire, wind, seismic) from the report + evidence.
export function buildVectors(d) {
  const { c, sig, ev } = d;
  const none = (title, state) => ({ title, level: 'IDLE', big: DASH, unit: '', state, rows: [], note: DASH });
  const out = [];

  const aq = ev.air_quality?.measurements, u = ev.air_quality?.units || {};
  const aqL = levelOf(c.air_quality_anomaly ?? 0);
  out.push(aq ? { title: 'Air quality', level: aqL, big: num(aq.pm25, 0), unit: 'µg/m³ PM2.5', state: `${aqL} · ${aq.station?.name || DASH}`,
    rows: [['PM2.5 density', `${num(aq.pm25, 0)} µg/m³ (${num(sig.pm25_anomaly_ratio, 2)}× baseline)`], ['PM10', `${num(aq.pm10, 0)} ${u.pm10 || ''}`], ['NO₂', `${num(aq.no2, 0)} ${u.no2 || ''}`], ['O₃', `${num(aq.o3, 0)} ${u.o3 || ''}`]], note: d.lines(/PM2\.5|particulate|sensor/i) || DASH }
    : none('Air quality', 'Source not queried or unavailable'));

  const fm = ev.fire?.measurements, fL = levelOf(c.proximity ?? 0);
  out.push(fm ? { title: 'Fire / thermal', level: fL, big: num(fm.max_frp_mw, 1), unit: 'MW peak FRP', state: `${fm.hotspot_count} hotspots · ${num(fm.radius_km, 0)} km radius`,
    rows: [['Nearest hotspot', `${num(fm.nearest_km, 0)} km ${d.dirLabel}`], ['Total FRP', `${num(fm.total_frp_mw, 1)} MW`], ['High confidence', `${fm.high_confidence_count} hotspots`], ['Downwind of fire', sig.is_downwind_of_fire ? 'YES' : 'NO']], note: d.lines(/hotspot|smoke/i) || DASH }
    : none('Fire / thermal', 'Source not queried or unavailable'));

  const wx = d.wx, wL = levelOf(c.wind_alignment ?? 0);
  out.push(d.ev.weather ? { title: 'Wind transport', level: wL, big: num(d.windSpeed, 0), unit: 'km/h wind', state: `From ${num(sig.wind_direction_deg, 0)}° (${compass(sig.wind_direction_deg)}) · ${wL} alignment`,
    rows: [['Surface wind', `${num(d.windSpeed, 0)} km/h`], ['Gusts', `${num(wx.wind_gusts_kmh, 0)} km/h`], ['Precipitation', `${num(wx.precipitation_mm, 1)} mm`], ['Humidity', `${num(wx.relative_humidity_pct, 0)}%`]], note: d.lines(/Wind|upwind|downwind/i) || DASH }
    : none('Wind transport', 'Source not queried or unavailable'));

  const eq = d.eq;
  out.push(eq ? { title: 'Seismic context', level: eq.event_count ? 'MODERATE' : 'LOW', big: eq.event_count ? `M${num(eq.max_magnitude, 1)}` : DASH, unit: '', state: `${eq.event_count} events in ${eq.window_days} days`,
    rows: [['Nearest event', eq.nearest_km != null ? `${num(eq.nearest_km, 0)} km` : DASH], ['Min magnitude', `M${num(eq.min_magnitude, 1)}`], ['Search radius', `${num(eq.radius_km, 0)} km`], ['Source status', String(ev.earthquake.status).toUpperCase()]], note: 'Seismicity is context only and is not part of the risk score.' }
    : none('Seismic context', 'Select Tier 3 to include seismic data'));
  return out;
}
