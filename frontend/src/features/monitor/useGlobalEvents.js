import { useSyncExternalStore } from 'react';
import { api } from '../../core/api/endpoints';

// In other words: one shared earthquake feed per (window, magnitude) pair. The sidebar, the monitor and
// the dispatch page all read the same copy, so the API is hit once per refresh instead of once per page.
// Requests are cancelled when superseded, and polling pauses while the tab is hidden.
const REFRESH_MS = 120000;
const stores = new Map();

function load(store) {
  store.ctrl?.abort();
  const ctrl = new AbortController();
  store.ctrl = ctrl;
  return api.globalEvents(store.params, ctrl.signal)
    .then((data) => { store.at = Date.now(); store.state = { data, error: null }; })
    .catch((e) => { if (e.name === 'AbortError') return; store.state = { ...store.state, error: e.message }; })
    .finally(() => { if (!ctrl.signal.aborted) store.listeners.forEach((l) => l()); });
}

function start(store) {
  if (!store.at || Date.now() - store.at > REFRESH_MS) load(store);
  store.timer = setInterval(() => { if (!document.hidden) load(store); }, REFRESH_MS);
  store.onVisible = () => { if (!document.hidden && Date.now() - store.at > REFRESH_MS) load(store); };
  document.addEventListener('visibilitychange', store.onVisible);
}

function stop(store) {
  clearInterval(store.timer);
  document.removeEventListener('visibilitychange', store.onVisible);
  store.ctrl?.abort();
}

function getStore(range, minMag) {
  const key = `${range}:${minMag}`;
  if (!stores.has(key)) {
    const store = { params: { window: range, minMag }, state: { data: null, error: null }, listeners: new Set(), at: 0 };
    store.subscribe = (listener) => {
      store.listeners.add(listener);
      if (store.listeners.size === 1) start(store);
      return () => { store.listeners.delete(listener); if (!store.listeners.size) stop(store); };
    };
    store.getSnapshot = () => store.state;
    store.reload = () => load(store);
    stores.set(key, store);
  }
  return stores.get(key);
}

export function useGlobalEvents({ window: range = 'day', minMag = 2.5 } = {}) {
  const store = getStore(range, minMag);
  const { data, error } = useSyncExternalStore(store.subscribe, store.getSnapshot);
  return { data, error, reload: store.reload };
}
