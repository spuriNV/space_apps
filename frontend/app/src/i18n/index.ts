// Tiny i18n: t('key', {vars}), the current language, and a switch that reloads (data text comes from the API with ?lang=es).
// Strings live in i18n/en.json + es.json (shared words) and i18n/parts/<area>.en.json / <area>.es.json (one pair per area).
// A missing Spanish key falls back to English; a missing English key shows the key itself.
import { useCallback } from 'react';
import baseEn from './en.json';
import baseEs from './es.json';

export type Lang = 'en' | 'es';
type Dict = Record<string, string>;

const merge = (base: Dict, parts: Record<string, unknown>): Dict => {
  const out: Dict = { ...base };
  for (const m of Object.values(parts)) Object.assign(out, (m as { default: Dict }).default ?? m);
  return out;
};
const EN: Dict = merge(baseEn as Dict, import.meta.glob('./parts/*.en.json', { eager: true }));
const ES: Dict = merge(baseEs as Dict, import.meta.glob('./parts/*.es.json', { eager: true }));

// Bundled English text that is data, not UI (example-field blurbs, editorial lists): { "English sentence": "Spanish sentence" } in parts/<area>.tx.json.
const TX: Dict = {};
for (const m of Object.values(import.meta.glob('./parts/*.tx.json', { eager: true }))) Object.assign(TX, (m as { default: Dict }).default ?? m);

const KEY = 'croplytics.lang';
function detect(): Lang {
  try {
    const q = new URLSearchParams(location.search).get('lang');
    if (q === 'es' || q === 'en') { try { localStorage.setItem(KEY, q); } catch { /* private mode */ } return q; }
  } catch { /* no location */ }
  try { const s = localStorage.getItem(KEY); if (s === 'es' || s === 'en') return s; } catch { /* private mode */ }
  try { return /^es/i.test(navigator.language || '') ? 'es' : 'en'; } catch { return 'en'; }
}

export const lang: Lang = typeof window === 'undefined' ? 'en' : detect();
export const isEs = lang === 'es';
if (typeof document !== 'undefined') document.documentElement.lang = lang;

/** Speech language codes that follow the app language (read aloud + voice input). */
export const speechLang = lang === 'es' ? 'es-US' : (typeof navigator !== 'undefined' && /^en/i.test(navigator.language || '') ? navigator.language : 'en-US');
/** Locale for number/date formatting. */
export const locale = lang === 'es' ? 'es-US' : 'en-US';

/** Translate a key; `{name}` placeholders are filled from vars. Works outside React too (the language is fixed per page load). */
export function t(key: string, vars?: Record<string, string | number>): string {
  let s = (lang === 'es' ? ES[key] : undefined) ?? EN[key] ?? key;
  if (vars) s = s.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m));
  return s;
}
/** Spanish for a bundled English data string (exact match), else the string unchanged. */
export const tx = (s: string): string => (lang === 'es' && TX[s]) || s;
/** Hook form, so components read naturally: `const t = useT()`. */
export function useT() { return useCallback(t, []); }

/** Switch language: remember it, drop ?lang from the URL and reload (keeps the #hash, so the field stays picked). */
export function setLang(next: Lang) {
  if (next === lang) return;
  try { localStorage.setItem(KEY, next); } catch { /* private mode */ }
  const u = new URL(location.href);
  u.searchParams.delete('lang');
  if (u.search !== location.search) location.replace(u.toString()); else location.reload();
}

/** Add `lang=es` to an API path when Spanish is on. */
export function withLang(path: string): string {
  if (lang !== 'es') return path;
  return path + (path.includes('?') ? '&' : '?') + 'lang=es';
}
