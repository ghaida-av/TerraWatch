import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../core/api/endpoints';
import { openStream } from '../core/api/sse';
import { derive } from './selectors';

const Ctx = createContext(null);
export const useInvestigation = () => useContext(Ctx);

const EMPTY_RUN = {
  report: null, evById: {}, evByKind: {}, citTotal: 0, events: [], stageT: [],
  running: false, t0: 0, lastDur: null, doneAt: null, runErr: null, runId: null, target: null, reqSources: [],
};

// In other words: this is the "brain" shared by every screen. One investigation at a time lives here.
export function InvestigationProvider({ children }) {
  const [S, setS] = useState({ health: null, rtt: null, sources: null, offline: false, ...EMPTY_RUN });
  const patch = useCallback((p) => setS((s) => ({ ...s, ...(typeof p === 'function' ? p(s) : p) })), []);
  const closeRef = useRef(null);

  const refreshHealth = useCallback(async () => {
    const t = performance.now();
    try {
      const [health, sources] = await Promise.all([api.health(), api.sources()]);
      patch({ health, sources, rtt: Math.round(performance.now() - t), offline: false });
    } catch {
      patch({ health: null, sources: null, rtt: null, offline: true });
    }
  }, [patch]);

  // Fetch every evidence envelope a report cites so screens can show real numbers.
  const loadEvidence = useCallback(async (ids = []) => {
    patch({ citTotal: ids.length });
    await Promise.all(ids.map(async (id) => {
      try {
        const e = await api.getEvidence(id);
        patch((s) => ({ evById: { ...s.evById, [id]: e }, evByKind: { ...s.evByKind, [e.kind]: e } }));
      } catch { /* evidence lives in server memory only; old ones may 404 */ }
    }));
  }, [patch]);

  const startInvestigation = useCallback(({ location, question, sources, countryHint }) => {
    if (closeRef.current) closeRef.current();
    patch({ ...EMPTY_RUN, running: true, t0: Date.now(), reqSources: sources });
    const finish = () => patch((s) => ({ running: false, lastDur: Date.now() - s.t0 }));
    closeRef.current = openStream(api.streamUrl({ location, question, sources, countryHint }), {
      onStage: (d) => {
        patch((s) => ({ events: [...s.events, d], stageT: [...s.stageT, Date.now()], runId: d.investigation_id || s.runId, target: d.target || s.target }));
        if (d.stage === 'evidence_collected') loadEvidence(d.citations);
      },
      onCompleted: async (d) => {
        patch((s) => ({ events: [...s.events, d], stageT: [...s.stageT, Date.now()], report: d.report, runId: d.investigation_id, doneAt: Date.now() }));
        finish();
        await loadEvidence(d.report.evidence_citations);
      },
      onError: (msg) => { patch({ runErr: msg }); finish(); },
    });
  }, [patch, loadEvidence]);

  // Show the latest saved investigation so a page refresh doesn't empty the UI.
  const loadLatest = useCallback(async () => {
    try {
      const list = await api.listInvestigations(1);
      if (!list.items.length) return;
      const report = await api.getInvestigation(list.items[0].investigation_id);
      patch({ report, runId: report.investigation_id, doneAt: Date.parse(list.items[0].created_at), target: report.target });
      await loadEvidence(report.evidence_citations);
    } catch { /* nothing stored yet */ }
  }, [patch, loadEvidence]);

  useEffect(() => { refreshHealth().then(loadLatest); const t = setInterval(refreshHealth, 30000); return () => { clearInterval(t); closeRef.current?.(); }; }, [refreshHealth, loadLatest]);

  const d = useMemo(() => derive(S), [S]);
  const value = useMemo(() => ({ S, d, startInvestigation, refreshHealth }), [S, d, startInvestigation, refreshHealth]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
