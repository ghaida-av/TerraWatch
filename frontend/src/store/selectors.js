import { compass } from '../core/utils/geo';

// In other words: turns the raw API report + evidence into the handy values the screens show.
export function derive(S) {
  const r = S.report, sig = r?.signals || {}, c = r?.components || {};
  const g = r?.evidence_graph || { nodes: [], relationships: [] };
  const ev = S.evByKind;
  const fm = ev.fire?.measurements || {}, wx = ev.weather?.measurements?.current || {};
  const aq = ev.air_quality?.measurements || {}, eq = ev.earthquake?.measurements, geo = ev.geo?.measurements;
  const rel = (t) => g.relationships.find((x) => x.type === t)?.properties;
  const fr = rel('THREATENS_LOCATION');
  const dirToFire = fr ? (fr.bearing_deg + 180) % 360 : null; // backend bearing is fire→target; flip it
  const kinds = Object.values(ev).filter((e) => e.kind !== 'geocode');
  const lines = (rx) => [...(r?.risk_indicators || []), ...(r?.key_findings || [])].find((s) => rx.test(s));
  const gc = geo?.by_category || {};
  const sumCat = (rx) => Object.entries(gc).filter(([k]) => rx.test(k)).reduce((a, [, v]) => a + v, 0);
  return {
    r, sig, c, g, fm, wx, aq, eq, geo, fr, dirToFire, lines, ev,
    id: r?.investigation_id || S.runId,
    target: r?.target || S.target,
    mode: S.sources?.mode || S.health?.mode || '—',
    okCount: kinds.filter((e) => e.status === 'ok').length,
    queried: kinds.length,
    hospitals: sumCat(/hospital/),
    windSpeed: sig.wind_speed_kmh ?? wx.wind_speed_kmh,
    dirLabel: dirToFire != null ? compass(dirToFire) : '',
  };
}
