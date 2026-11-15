import { motionOff } from '../a11y/prefs';
// Count a number up or down to `target` over `ms`; jumps straight there under prefers-reduced-motion.
import { useEffect, useRef, useState } from 'react';

export function useCountUp(target: number, ms = 600): number {
  const [v, setV] = useState(0);
  const from = useRef(0);
  useEffect(() => {
    const still = motionOff();
    if (still) { from.current = target; setV(target); return; }
    const a = from.current, t0 = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const k = Math.min(1, (t - t0) / ms), e = 1 - Math.pow(1 - k, 3);
      const x = a + (target - a) * e;
      from.current = x; setV(x);
      if (k < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, ms]);
  return v;
}
