// Display preferences kept in localStorage: "Outdoor / high contrast" (bigger type, bold ink, no light greys, AAA body text) and
// "Pause all motion" (replay, rain, fly-ins, transitions). Both are applied as data attributes on <html> before React renders.
import { useSyncExternalStore } from 'react';

const KEY = 'croplytics.a11y';
export interface Prefs { outdoor: boolean; pause: boolean }
const read = (): Prefs => { try { return { outdoor: false, pause: false, ...JSON.parse(localStorage.getItem(KEY) ?? '{}') }; } catch { return { outdoor: false, pause: false }; } };
let state: Prefs = read();
const subs = new Set<() => void>();
export function applyPrefs() {
  const h = document.documentElement;
  h.dataset.outdoor = state.outdoor ? '1' : '0';
  h.dataset.pause = state.pause ? '1' : '0';
}
export function setPref<K extends keyof Prefs>(k: K, v: Prefs[K]) {
  state = { ...state, [k]: v };
  try { localStorage.setItem(KEY, JSON.stringify(state)); } catch { /* private mode: still applies for this visit */ }
  applyPrefs();
  subs.forEach((f) => f());
}
export const usePrefs = () => useSyncExternalStore((f) => { subs.add(f); return () => { subs.delete(f); }; }, () => state);
/** True when motion should be off: the person paused it, or the device asks for reduced motion. */
export const motionOff = () => state.pause || (typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches);
export const getPrefs = () => state;
