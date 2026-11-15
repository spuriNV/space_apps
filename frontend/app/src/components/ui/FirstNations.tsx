// Working with First Nations (BC fields). Public facts only; nothing speaks for a Nation.
// Honest: this demo field is not on reserve; nearest reserves and Splatsin on the lower Salmon River.
import { useEffect, useState } from 'react';
import type { FirstNations, Location } from '../../types';
import { linkOf } from '../../types';
import { getFirstNations } from '../../api';
import { isBC } from './shared';

const titleCase = (s: string) => s.toLowerCase().replace(/(^|[\s(])(\p{L})/gu, (_m, a: string, b: string) => a + b.toUpperCase());

/** Compact card for the dock. Detail stays behind "More". */
export function FirstNationsCard({ loc }: { loc: Location }) {
  const [fn, setFn] = useState<FirstNations | null | undefined>(undefined);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (!isBC(loc)) return;
    let ok = true;
    getFirstNations(loc.id).then((v) => ok && setFn(v));
    return () => { ok = false; };
  }, [loc.id]);
  if (!isBC(loc)) return null;
  const s = loc.first_nations;
  if (!s && fn === null) return null;
  if (!s && fn === undefined) return <p className="fn-loading muted">Loading Nations context…</p>;
  const statement = fn?.statement ?? s!.statement;
  const onReserve = fn?.field_on_reserve ?? s!.field_on_reserve;
  const km = fn?.nearest_km ?? s!.nearest_km;
  const nation = fn?.nearest_nation ?? s!.nearest_nation;
  const reserve = fn?.nearest_reserve ?? s!.nearest_reserve;
  const lower = fn?.lower_river_nation ?? (s ? { nation: s.lower_river_nation, url: 'https://splatsin.ca/your-government/land', reserve: 'SALMON RIVER 1 (SPLATSIN)' } : null);
  const near = (fn?.nearby ?? []).filter((r) => r.distance_to_field_km <= 20).slice(0, 4);
  return (
    <section className="fn" data-testid="first-nations">
      <h2 className="fn-h">Near First Nations lands</h2>
      <p className="fn-statement">{statement}</p>
      <ul className="fn-lines">
        <li>{onReserve ? 'This field is on reserve land.' : `Not on reserve. Nearest: ${titleCase(reserve)} (~${km} km, ${nation}).`}</li>
        {lower && (
          <li>
            Lower Salmon River: {lower.nation}
            {lower.reserve ? ` · ${titleCase(lower.reserve)}` : ''}
            {linkOf(lower) && <> · <a href={linkOf(lower)!} target="_blank" rel="noreferrer">lands page</a></>}
          </li>
        )}
      </ul>
      <button type="button" className="fn-more-btn" onClick={() => setOpen(!open)} data-testid="fn-toggle">
        {open ? 'Less' : 'Nearby reserves'}
      </button>
      {open && (
        <div className="fn-more" data-testid="first-nations-detail">
          {fn === undefined ? <p className="muted">Loading…</p> : fn === null ? <p className="muted">More detail not loaded.</p> : (
            <>
              <ul className="fn-near">
                {near.map((r) => (
                  <li key={r.reserve}><b>{r.distance_to_field_km.toFixed(1)} km</b><span>{titleCase(r.reserve)}</span><small>{r.nation}</small></li>
                ))}
              </ul>
              {fn.notes?.[0] && <p className="fn-note">{fn.notes[0]}</p>}
              <cite>{fn.source?.title ?? 'BC Data Catalogue'}{linkOf(fn.source) && <> · <a href={linkOf(fn.source)!} target="_blank" rel="noreferrer">Source</a></>}</cite>
            </>
          )}
        </div>
      )}
    </section>
  );
}
