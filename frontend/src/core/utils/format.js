export const DASH = '—';
export const num = (v, d = 1) => (v == null || Number.isNaN(+v) ? DASH : (+v).toFixed(d));
export const pct = (v) => (v == null ? DASH : `${Math.round(v * 100)}%`);
export const lat$ = (v) => (v == null ? DASH : `${Math.abs(v).toFixed(4)}° ${v >= 0 ? 'N' : 'S'}`);
export const lon$ = (v) => (v == null ? DASH : `${Math.abs(v).toFixed(4)}° ${v >= 0 ? 'E' : 'W'}`);
export const hhmm = (iso) => (iso ? `${new Date(iso).toISOString().slice(11, 16)} UTC` : DASH);
export const hhmmss = (ms) => `${new Date(ms).toISOString().slice(11, 19)} UTC`;
export const ago = (iso) => {
  if (!iso) return DASH;
  const m = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  return m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} d ago`;
};
