import { useCallback, useEffect, useState } from 'react';
import { api } from '../../core/api/endpoints';

// In other words: loads the planet-wide earthquake list and refreshes it every 2 minutes.
export function useGlobalEvents({ window = 'day', minMag = 2.5 } = {}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const load = useCallback(async () => {
    try { setData(await api.globalEvents({ window, minMag })); setError(null); }
    catch (e) { setError(e.message); }
  }, [window, minMag]);
  useEffect(() => { load(); const t = setInterval(load, 120000); return () => clearInterval(t); }, [load]);
  return { data, error, reload: load };
}
