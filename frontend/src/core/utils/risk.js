// Same cut-offs as backend geo_analysis/pipeline.py
export const levelOf = (s) => (s >= 0.7 ? 'CRITICAL' : s >= 0.5 ? 'HIGH' : s >= 0.25 ? 'MODERATE' : 'LOW');

// In other words: one colour set per level, reused by badges, dots and map rings.
export const LEVEL = {
  LOW:      { text: 'text-emerald-300', bg: 'bg-emerald-500/15', border: 'border-emerald-500/40', hex: '#34d399' },
  MODERATE: { text: 'text-amber-300',   bg: 'bg-amber-500/15',   border: 'border-amber-500/40',   hex: '#fbbf24' },
  HIGH:     { text: 'text-orange-300',  bg: 'bg-orange-500/15',  border: 'border-orange-500/40',  hex: '#fb923c' },
  CRITICAL: { text: 'text-red-300',     bg: 'bg-red-500/15',     border: 'border-red-500/40',     hex: '#f87171' },
  IDLE:     { text: 'text-slate-400',   bg: 'bg-slate-500/10',   border: 'border-slate-500/30',   hex: '#64748b' },
};
export const levelStyle = (l) => LEVEL[l] || LEVEL.IDLE;
