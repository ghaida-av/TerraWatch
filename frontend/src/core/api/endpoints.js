import { request } from './client';
import { API_BASE } from '../config';

// In other words: one small function per backend endpoint. Pages never write URLs by hand.
export const api = {
  health: () => request('/health'),
  sources: () => request('/sources'),
  globalEvents: ({ window = 'day', minMag = 2.5, limit = 150 } = {}, signal) =>
    request(`/monitor/events?window=${window}&min_mag=${minMag}&limit=${limit}`, { signal }),
  listInvestigations: (limit = 20, offset = 0) => request(`/investigations?limit=${limit}&offset=${offset}`),
  getInvestigation: (id) => request(`/investigations/${id}`),
  getGraph: (id) => request(`/investigations/${id}/graph`),
  getEvidence: (id) => request(`/evidence/${id}`),
  streamUrl: ({ location, question, sources, countryHint }) => {
    const p = new URLSearchParams({ location, question });
    (sources || []).forEach((s) => p.append('sources', s));
    if (countryHint) p.set('country_hint', countryHint);
    return `${API_BASE}/investigations/stream?${p}`;
  },
};
