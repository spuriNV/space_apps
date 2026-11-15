// One "More detail" switch for the whole app, remembered for the browser session.
// The farmer's default view shows the decision; adviser detail (sources, NASA list, ML, stress weeks, percentiles,
// ranges, glossary, insurance, earlier years, 3D) is one tap away. Elements marked .d-only appear only with detail on.
import { createContext, useContext, useState } from 'react';
import Icon from '../Icons';

const KEY = 'croplytics.detail';
const read = () => { try { return sessionStorage.getItem(KEY) === '1'; } catch { return false; } };
export function useDetailState() {
  const [on, setOn] = useState(read);
  const set = (v: boolean) => { setOn(v); try { sessionStorage.setItem(KEY, v ? '1' : '0'); } catch { /* private mode */ } };
  return [on, set] as const;
}
export const DetailCtx = createContext<{ on: boolean; set: (v: boolean) => void }>({ on: false, set: () => {} });
export const useDetail = () => useContext(DetailCtx);

/** The disclosure at the end of a screen. */
export function MoreDetail({ what }: { what: string }) {
  const d = useDetail();
  return (
    <button className={`more-detail ${d.on ? 'on' : ''}`} onClick={() => d.set(!d.on)} aria-expanded={d.on} data-testid="more-detail">
      <span><b>{d.on ? 'Less detail' : 'More detail'}</b><small>{d.on ? 'Back to the short version' : what}</small></span><Icon name="chevdown" size={20} />
    </button>
  );
}
