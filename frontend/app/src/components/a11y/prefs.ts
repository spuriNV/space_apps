// Display and access preferences kept in localStorage (every read and write inside try/catch): "Outdoor / high contrast",
// "Pause all motion", Simple mode, text size (100 to 200%), theme (system / light / dark), dyslexia-friendly text, Large print
// for the adviser brief and Lite mode. They are applied as data attributes and one CSS variable on <html> before React renders.
import { useSyncExternalStore } from 'react';

const KEY = 'croplytics.a11y';
export type Theme = 'system' | 'light' | 'dark';
export type LiteSetting = 'auto' | 'on' | 'off';
export interface Prefs { outdoor: boolean; pause: boolean; simple: boolean; textPct: number; theme: Theme; dyslexia: boolean; largePrint: boolean; lite: LiteSetting }
const DEFAULTS: Prefs = { outdoor: false, pause: false, simple: false, textPct: 100, theme: 'system', dyslexia: false, largePrint: false, lite: 'auto' };
const read = (): Prefs => {
  try {
    const p = { ...DEFAULTS, ...JSON.parse(localStorage.getItem(KEY) ?? '{}') } as Prefs;
    p.textPct = Math.min(200, Math.max(100, Math.round(Number(p.textPct) || 100)));
    if (!['system', 'light', 'dark'].includes(p.theme)) p.theme = 'system';
    if (!['auto', 'on', 'off'].includes(p.lite)) p.lite = 'auto';
    return p;
  } catch { return { ...DEFAULTS }; }
};
let state: Prefs = read();
const subs = new Set<() => void>();

/** Data Saver is on, or the connection is slow (2g or 3g). */
export function slowConnection(): boolean {
  const c = (typeof navigator !== 'undefined' ? (navigator as unknown as { connection?: { saveData?: boolean; effectiveType?: string } }).connection : undefined);
  return !!c && (c.saveData === true || /^(slow-2g|2g|3g)$/.test(c.effectiveType ?? ''));
}
/** Lite mode is in force: turned on, or "Automatic" on a slow or Data Saver connection. */
export const liteOn = () => state.lite === 'on' || (state.lite === 'auto' && slowConnection());
const dark = () => state.theme === 'dark' || (state.theme === 'system' && typeof matchMedia === 'function' && matchMedia('(prefers-color-scheme: dark)').matches);

export function applyPrefs() {
  const h = document.documentElement;
  h.dataset.outdoor = state.outdoor ? '1' : '0';
  h.dataset.pause = state.pause ? '1' : '0';
  h.dataset.simple = state.simple ? '1' : '0';
  h.dataset.dys = state.dyslexia ? '1' : '0';
  h.dataset.largeprint = state.largePrint ? '1' : '0';
  h.dataset.bigtext = state.textPct >= 150 ? '1' : '0';
  h.dataset.lite = liteOn() ? '1' : '0';
  h.dataset.theme = dark() ? 'dark' : 'light';
  h.style.setProperty('--tx', String(state.textPct / 100));
  h.style.fontSize = `${state.textPct}%`;
}
export function setPref<K extends keyof Prefs>(k: K, v: Prefs[K]) {
  state = { ...state, [k]: v };
  try { localStorage.setItem(KEY, JSON.stringify(state)); } catch { /* private mode: still applies for this visit */ }
  applyPrefs();
  subs.forEach((f) => f());
}
// the system theme and the connection can change while the page is open
if (typeof matchMedia === 'function') matchMedia('(prefers-color-scheme: dark)').addEventListener?.('change', () => { if (state.theme === 'system') { applyPrefs(); subs.forEach((f) => f()); } });
if (typeof navigator !== 'undefined') (navigator as unknown as { connection?: EventTarget }).connection?.addEventListener?.('change', () => { applyPrefs(); subs.forEach((f) => f()); });

// the snapshot includes the derived Lite flag so components re-render when the connection changes
let snap = { ...state, liteNow: liteOn() };
const snapshot = () => { const l = liteOn(); if (snap.liteNow !== l || Object.keys(DEFAULTS).some((k) => (snap as Record<string, unknown>)[k] !== (state as unknown as Record<string, unknown>)[k])) snap = { ...state, liteNow: l }; return snap; };
export const usePrefs = () => useSyncExternalStore((f) => { subs.add(f); return () => { subs.delete(f); }; }, snapshot);
/** True when motion should be off: the person paused it, or the device asks for reduced motion. */
export const motionOff = () => state.pause || (typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches);
export const getPrefs = () => state;
