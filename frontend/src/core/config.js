// In other words: where the backend lives. Default "/api" works with the Vite dev proxy.
export const API_BASE = (import.meta.env.VITE_API_BASE || '/api').replace(/\/$/, '');
