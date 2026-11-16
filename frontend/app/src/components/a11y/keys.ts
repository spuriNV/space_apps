import { useEffect, useRef } from 'react';

const typing = (el: Element | null) => {
  if (!el) return false;
  const t = (el as HTMLElement).tagName;
  return t === 'INPUT' || t === 'TEXTAREA' || t === 'SELECT' || (el as HTMLElement).isContentEditable;
};
/** One-key shortcuts. They do nothing while the person is typing in a field, or with Ctrl, Alt or Cmd held. */
export function useShortcuts(h: { step: (n: number) => void; search: () => void; list: () => void; read: () => void; panel: () => void; help: () => void }) {
  const ref = useRef(h); ref.current = h;
  useEffect(() => {
    const on = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.altKey || e.metaKey || e.defaultPrevented || typing(document.activeElement)) return;
      const k = e.key;
      if (/^[1-5]$/.test(k)) { e.preventDefault(); ref.current.step(+k); }
      else if (k === '/') { e.preventDefault(); ref.current.search(); }
      else if (k === 'l' || k === 'L') { e.preventDefault(); ref.current.list(); }
      else if (k === 'r' || k === 'R') { e.preventDefault(); ref.current.read(); }
      else if (k === 'm' || k === 'M') { e.preventDefault(); ref.current.panel(); }
      else if (k === '?') { e.preventDefault(); ref.current.help(); }
    };
    document.addEventListener('keydown', on);
    return () => document.removeEventListener('keydown', on);
  }, []);
}
