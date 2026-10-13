import { useEffect, useRef, useState } from 'react';

const COUNTRY_API = 'https://api.bigdatacloud.net/data/reverse-geocode-client';
const CACHE_KEY = 'terrawatch-country-cache-v1';
const CACHE_TTL = 30 * 24 * 60 * 60 * 1000;
const countryCache = new Map();

function cacheKey(lat, lon) {
  return `${Number(lat).toFixed(2)},${Number(lon).toFixed(2)}`;
}

function readCache(key) {
  if (countryCache.has(key)) return countryCache.get(key);
  try {
    const saved = JSON.parse(localStorage.getItem(CACHE_KEY) || '{}');
    const entry = saved[key];
    if (entry && Date.now() - entry.savedAt < CACHE_TTL) {
      countryCache.set(key, entry.country);
      return entry.country;
    }
  } catch (error) {
    if (!(error instanceof SyntaxError) && !(error instanceof DOMException)) throw error;
    // Storage may be unavailable; in-memory lookups still work.
  }
  return null;
}

async function lookupCountry(lat, lon) {
  const key = cacheKey(lat, lon);
  const cached = readCache(key);
  if (cached) return cached;

  const query = new URLSearchParams({
    latitude: String(lat),
    longitude: String(lon),
    localityLanguage: 'en',
  });
  const response = await fetch(`${COUNTRY_API}?${query}`);
  if (!response.ok) throw new Error(`Country lookup failed (HTTP ${response.status})`);
  const result = await response.json();
  const country = result.countryCode && result.countryName
    ? { code: result.countryCode.toLowerCase(), name: result.countryName }
    : { code: null, name: 'International waters' };

  countryCache.set(key, country);
  try {
    const saved = JSON.parse(localStorage.getItem(CACHE_KEY) || '{}');
    saved[key] = { country, savedAt: Date.now() };
    const recent = Object.entries(saved)
      .sort(([, left], [, right]) => right.savedAt - left.savedAt)
      .slice(0, 300);
    localStorage.setItem(CACHE_KEY, JSON.stringify(Object.fromEntries(recent)));
  } catch (error) {
    if (!(error instanceof DOMException)) throw error;
    // A blocked or full local storage cache should not hide a resolved country.
  }
  return country;
}

export default function CountryFlag({ lat, lon }) {
  const badgeRef = useRef(null);
  const [country, setCountry] = useState(() => readCache(cacheKey(lat, lon)));
  const [lookupFailed, setLookupFailed] = useState(false);

  useEffect(() => {
    let active = true;
    const badge = badgeRef.current;
    const root = badge?.closest('.monitor-event-list');
    const resolve = () => {
      lookupCountry(lat, lon)
        .then((result) => { if (active) setCountry(result); })
        .catch(() => { if (active) setLookupFailed(true); });
    };

    if (typeof IntersectionObserver === 'undefined') {
      resolve();
      return () => { active = false; };
    }

    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        observer.disconnect();
        resolve();
      }
    }, { root, rootMargin: '100px 0px' });
    if (badge) observer.observe(badge);
    return () => {
      active = false;
      observer.disconnect();
    };
  }, [lat, lon]);

  return (
    <span ref={badgeRef} className="monitor-country" title={country?.name || (lookupFailed ? 'Country lookup unavailable' : 'Resolving country')}>
      {country?.code
        ? <img src={`https://flagcdn.com/24x18/${country.code}.png`} alt={`${country.name} flag`} width="24" height="18" loading="lazy" />
        : <span aria-hidden="true">{country ? '🌐' : lookupFailed ? '—' : '…'}</span>}
      <span className="monitor-country-name">{country?.name || (lookupFailed ? 'Country unavailable' : 'Locating')}</span>
    </span>
  );
}
