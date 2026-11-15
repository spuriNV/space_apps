// Small fetch hook shared by "This week" and "Nation tools": one route, friendly states.
// 404 = this place has no such data, 429 = busy (Retry-After, one automatic retry when it is short), anything else = failed.
import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { API_BASE } from '../../api';

export type RouteState<T> =
  | { kind: 'loading' }
  | { kind: 'ok'; data: T }
  | { kind: 'missing' }
  | { kind: 'busy'; seconds: number | null }
  | { kind: 'error' };

const lastGood = new Map<string, unknown>(); // the last good answer per route: shown while a refresh runs or after a failed one
const BACKOFF = [800, 2000, 4500]; // automatic retries after a failure or a 5xx

export function useRoute<T>(path: string | null, ms = 30000): RouteState<T> & { reload: () => void; stale?: boolean } {
  const [st, setSt] = useState<RouteState<T>>(() => (path && lastGood.has(path) ? { kind: 'ok', data: lastGood.get(path) as T } : { kind: 'loading' }));
  const [stale, setStale] = useState(false);
  const [n, setN] = useState(0);
  const reload = useCallback(() => setN((x) => x + 1), []);
  useEffect(() => {
    if (!path) { setSt({ kind: 'loading' }); return; }
    let live = true, retry = 0, attempt = 0, timer: ReturnType<typeof setTimeout> | undefined;
    let ctl = new AbortController();
    setStale(false);
    setSt(lastGood.has(path) ? { kind: 'ok', data: lastGood.get(path) as T } : (s) => (s.kind === 'ok' ? s : { kind: 'loading' }));
    const fail = () => {
      if (!live) return;
      if (attempt < BACKOFF.length) { retry = window.setTimeout(go, BACKOFF[attempt++]); return; }
      if (lastGood.has(path)) { setStale(true); return; } // keep the last good value, flagged as old
      setSt({ kind: 'error' });
    };
    const go = () => {
    ctl = new AbortController(); timer = setTimeout(() => ctl.abort(), ms);
    fetch(`${API_BASE}${path}`, { signal: ctl.signal })
      .then(async (r) => {
        if (!live) return;
        if (r.status === 404) return setSt({ kind: 'missing' });
        if (r.status === 429) {
          const s = parseInt(r.headers.get('Retry-After') ?? '', 10);
          const sec = Number.isFinite(s) && s > 0 ? s : null;
          setSt({ kind: 'busy', seconds: sec });
          if (sec && sec <= 20 && n === 0) retry = window.setTimeout(() => live && setN((x) => x + 1), sec * 1000 + 300);
          return;
        }
        if (!r.ok) return fail();
        const data = (await r.json()) as T;
        if (!live) return;
        lastGood.set(path, data); setStale(false); setSt({ kind: 'ok', data });
      })
      .catch(fail)
      .finally(() => clearTimeout(timer));
    };
    go();
    return () => { live = false; ctl.abort(); clearTimeout(timer); clearTimeout(retry); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, n]);
  return { ...st, reload, stale };
}

/** The quiet "busy" / "failed" line with a retry button. */
export function RouteProblem({ st, what, reload }: { st: RouteState<unknown>; what: string; reload: () => void }): ReactNode {
  if (st.kind === 'busy') return <div className="wk-note" role="status"><span>Busy right now. {st.seconds ? `Try again in about ${st.seconds} seconds.` : 'Try again in a moment.'}</span><button className="btn btn-outline btn-sm" onClick={reload}>Try again</button></div>;
  if (st.kind === 'error') return <div className="wk-note" role="status"><span>{what} is not available right now.</span><button className="btn btn-outline btn-sm" onClick={reload}>Try again</button></div>;
  return null;
}

export const SKEL = (n = 3) => <div className="wk-skel" aria-label="Loading">{Array.from({ length: n }, (_, i) => <span key={i} className="skel" style={{ width: `${88 - i * 18}%` }} />)}</div>;
