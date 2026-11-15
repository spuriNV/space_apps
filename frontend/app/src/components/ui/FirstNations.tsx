// "Working with First Nations" (BC fields only). Farmer default: the project's statement, whether the field is on reserve land,
// and the Nation on the lower river with its own page. More detail: nearby reserves by distance, how we would approach the
// Nations, the principles (OCAP®, CARE, TCPS 2 ch. 9), public contact pages and the water and salmon timeline.
// Respectful and factual: public facts and links only, nothing that speaks for a Nation, no imagery of people.
import { useEffect, useState } from 'react';
import type { FirstNations, Location } from '../../types';
import { linkOf } from '../../types';
import { getFirstNations } from '../../api';
import { fmtDate } from '../../lib';
import { t } from '../../i18n';

/** "SALMON RIVER 1 (SPLATSIN)" -> "Salmon River 1 (Splatsin)" */
export const reserveName = (s: string) => s.toLowerCase().replace(/(^|[\s(])(\p{L})/gu, (_m, a: string, b: string) => a + b.toUpperCase());
const when = (d: string) => (/^\d{4}-\d{2}-\d{2}$/.test(d) ? fmtDate(d) : d);
const NEAR_KM = 20;

export function FirstNationsCard({ loc }: { loc: Location }) {
  const [fn, setFn] = useState<FirstNations | null | undefined>(undefined);
  useEffect(() => { let ok = true; getFirstNations(loc.id).then((v) => ok && setFn(v)); return () => { ok = false; }; }, [loc.id]);
  const s = loc.first_nations;
  if (!s && !fn) return null;
  const statement = fn?.statement ?? s!.statement;
  const onReserve = fn?.field_on_reserve ?? s!.field_on_reserve;
  const km = fn?.nearest_km ?? s!.nearest_km, nation = fn?.nearest_nation ?? s!.nearest_nation, reserve = fn?.nearest_reserve ?? s!.nearest_reserve;
  const lower = fn?.lower_river_nation ?? (s ? { nation: s.lower_river_nation, url: '', reserve: '' } : null);
  const river = loc.water_context?.watershed.split(/[(;,]/)[0].trim() || t('ui.fn.river');
  const near = (fn?.nearby ?? []).filter((r) => r.distance_to_field_km <= NEAR_KM).sort((a, b) => a.distance_to_field_km - b.distance_to_field_km);
  const rest = (fn?.nearby ?? []).filter((r) => r.distance_to_field_km > NEAR_KM);
  return (
    <section className="fn" data-testid="first-nations">
      <h2 className="fp-h">{t('ui.fn.h')}</h2>
      <p className="fn-statement">{statement}</p>
      <ul className="fn-lines">
        <li>{onReserve ? t('ui.fn.on') : t('ui.fn.off', { reserve: reserveName(reserve), km, nation })}</li>
        {lower && <li>{t('ui.fn.lower', { river })} {lower.nation}{lower.reserve ? ` (${reserveName(lower.reserve)})` : ''}.{linkOf(lower) && <> <a href={linkOf(lower)!} target="_blank" rel="noreferrer">{t('ui.fn.landspage', { nation: lower.nation })}</a></>}</li>}
      </ul>
      <div className="d-only fn-more" data-testid="first-nations-detail">
        {fn === undefined ? <p className="muted">{t('ui.loading')}</p> : fn === null ? <p className="gap-line">{t('ui.fn.unavail')}</p> : <>
          <h3>{t('ui.fn.near')}</h3>
          <ul className="fn-near">
            {near.map((r) => <li key={r.reserve}><b>{r.distance_to_field_km.toFixed(1)} km</b><span>{reserveName(r.reserve)}</span><small>{r.nation}</small></li>)}
          </ul>
          {rest.length > 0 && <p className="how">{t('ui.fn.more', { n: rest.length, km: Math.ceil(Math.max(...rest.map((r) => r.distance_to_field_km))), nations: [...new Set(rest.map((r) => r.nation))].join(', ') })}</p>}
          {fn.notes?.[0] && <p className="how">{fn.notes[0]}</p>}

          <h3>{t('ui.fn.start')}</h3>
          <ol className="fn-steps">{fn.engagement_steps.map((x) => <li key={x}>{x}</li>)}</ol>

          <h3>{t('ui.fn.principles')}</h3>
          <ul className="fn-list">{fn.principles.map((x) => <li key={x.id}>{linkOf(x) ? <a href={linkOf(x)!} target="_blank" rel="noreferrer">{x.name}</a> : <b>{x.name}</b>}<span>{x.description}</span></li>)}</ul>

          <h3>{t('ui.fn.contacts')}</h3>
          <ul className="fn-list">{fn.contacts.map((x) => <li key={x.url + x.nation}>{linkOf(x) ? <a href={linkOf(x)!} target="_blank" rel="noreferrer">{x.nation}</a> : <b>{x.nation}</b>}<span>{x.department}</span></li>)}</ul>

          <h3>{t('ui.fn.timeline', { from: fn.water_timeline[0]?.date.slice(0, 4) ?? '', to: fn.water_timeline[fn.water_timeline.length - 1]?.date.slice(0, 4) ?? '' })}</h3>
          <ul className="fn-time">
            {fn.water_timeline.map((x) => <li key={x.date + x.title}><time>{when(x.date)}</time><span>{x.title}{linkOf(x) && <> <a href={linkOf(x)!} target="_blank" rel="noreferrer">{t('ui.source')}</a></>}</span></li>)}
          </ul>
          <cite>{fn.source?.title ?? t('ui.fn.catalogue')}{fn.notes?.[1] ? `. ${fn.notes[1]}` : ''}</cite>
        </>}
      </div>
    </section>
  );
}
