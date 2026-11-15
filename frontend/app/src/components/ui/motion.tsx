// Small motion helpers. CSS does almost all of the motion (styles.css, "Motion"); these cover what CSS cannot:
// a number counting up to a new reading, and a check for reduced motion.
import { useEffect, useRef, useState } from 'react';

export const reducedMotion = () => typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
const easeOut = (k: number) => 1 - Math.pow(1 - k, 4);

/** A reading that counts up from 0 when it first appears (and glides to a new value when the date changes).
 *  Tabular figures keep the width steady, so only the digits change. */
export function CountUp({ value, dec = 0, ms = 650 }: { value: number; dec?: number; ms?: number }) {
  const [v, setV] = useState(() => (reducedMotion() ? value : 0));
  const shown = useRef(v);
  useEffect(() => {
    if (reducedMotion()) { shown.current = value; setV(value); return; }
    const from = shown.current, t0 = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const k = Math.min(1, (now - t0) / ms);
      shown.current = from + (value - from) * easeOut(k);
      setV(shown.current);
      if (k < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, ms]);
  return <span className="tnum">{v.toFixed(dec)}</span>;
}
