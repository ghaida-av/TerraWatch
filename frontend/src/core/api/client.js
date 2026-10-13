import { API_BASE } from '../config';

// In other words: one place that calls fetch, checks the status, and turns errors into readable messages.
export async function request(path, options) {
  const res = await fetch(API_BASE + path, options);
  if (!res.ok) {
    let detail = '';
    try { detail = (await res.json()).detail; } catch { /* body was not JSON */ }
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return res.json();
}
