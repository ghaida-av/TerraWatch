// In other words: small map maths used only for drawing (the real risk maths lives in the backend).
export const compass = (deg) =>
  ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'][Math.round((((deg % 360) + 360) % 360) / 45) % 8];

// Point reached by travelling `km` from (lat, lon) along bearing `brg` degrees.
export function destination(lat, lon, brg, km) {
  const R = 6371, d = km / R, t = (brg * Math.PI) / 180, p1 = (lat * Math.PI) / 180, l1 = (lon * Math.PI) / 180;
  const p2 = Math.asin(Math.sin(p1) * Math.cos(d) + Math.cos(p1) * Math.sin(d) * Math.cos(t));
  const l2 = l1 + Math.atan2(Math.sin(t) * Math.sin(d) * Math.cos(p1), Math.cos(d) - Math.sin(p1) * Math.sin(p2));
  return [(p2 * 180) / Math.PI, ((((l2 * 180) / Math.PI) + 540) % 360) - 180];
}
