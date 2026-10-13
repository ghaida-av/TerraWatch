// In other words: small helpers that turn the raw earthquake list into the things the design shows.

// Severity -> the label + colour the design uses on the right of each event row.
export const STATUS = {
  CRITICAL: ['CRITICAL_ALERT', 'text-red-400'],
  HIGH: ['AMBER_ALERT', 'text-amber-300'],
  MODERATE: ['WATCH', 'text-yellow-200'],
  LOW: ['NOMINAL', 'text-emerald-400'],
};

export const topLevel = (levels) => ['CRITICAL', 'HIGH', 'MODERATE', 'LOW'].find((l) => levels?.[l] > 0) || null;

// 8 "sectors" A–H = 45° longitude bands around the planet (real counts from the feed).
export function sectorCounts(events) {
  const rows = 'ABCDEFGH'.split('').map((k) => ({ k, n: 0, high: 0 }));
  events.forEach((e) => {
    const i = Math.min(7, Math.floor((((e.lon + 180) % 360) + 360) % 360 / 45));
    rows[i].n += 1;
    if (e.level === 'HIGH' || e.level === 'CRITICAL') rows[i].high += 1;
  });
  return rows;
}

// Events per time bucket (oldest -> newest) for the "progression" line charts.
const CFG = { hour: { n: 12, ms: 300000 }, day: { n: 24, ms: 3600000 }, week: { n: 7, ms: 86400000 } };
export function progression(events, window = 'day') {
  const { n, ms } = CFG[window] || CFG.day, now = Date.now();
  const rows = Array.from({ length: n }, (_, i) => ({ i, n: 0 }));
  events.forEach((e) => {
    const idx = n - 1 - Math.floor((now - new Date(e.time).getTime()) / ms);
    if (idx >= 0 && idx < n) rows[idx].n += 1;
  });
  return rows;
}

export const clock = (iso) => (iso ? new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—');
export const gmtStamp = (iso) => (iso ? `${new Date(iso).toISOString().slice(8, 10)} ${new Date(iso).toLocaleString('en', { month: 'short', timeZone: 'UTC' }).toUpperCase()} ${new Date(iso).getUTCFullYear()} - UPDATED ${new Date(iso).toISOString().slice(11, 19)} GMT` : '—');
