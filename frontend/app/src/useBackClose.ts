// Android / browser Back closes an open dialog or card instead of leaving the page.
// While `open`, one history entry is pushed; Back (popstate) calls onClose. Closing any other way removes that entry again.
import { useEffect, useRef } from 'react';

let ignore = 0; // popstate events we caused ourselves (cleanup history.back())

export function useBackClose(open: boolean, onClose: () => void) {
  const cb = useRef(onClose);
  cb.current = onClose;
  useEffect(() => {
    if (!open) return;
    let byBack = false;
    const mark = { bc: Math.random() };
    try { history.pushState({ ...(history.state ?? {}), ...mark }, ''); } catch { return; }
    const onPop = () => {
      if (ignore > 0) { ignore--; return; }
      byBack = true;
      cb.current();
    };
    window.addEventListener('popstate', onPop);
    return () => {
      window.removeEventListener('popstate', onPop);
      if (!byBack && history.state && (history.state as { bc?: number }).bc === mark.bc) { ignore++; history.back(); }
    };
  }, [open]);
}
