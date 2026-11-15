// "This week" card at the top of Field now: GET /api/locations/{id}/this_week.
// Irrigation verdict + 7-day need strip, field access chips, 7-day forecast, alerts. Sections follow `sections.*`:
// unavailable / not_applicable parts are hidden, fallback / partial parts carry a quiet tag. Hidden for my_ ids (404).
import { useState } from 'react';
import type { Location } from '../../types';
import { RouteProblem, SKEL, useRoute } from './useRoute';
import './week.css';

interface V { value: number | null }
interface Day { date: string; weekday: string; rain_mm: V; tmax_c: V; tmin_c: V }
interface IrrDay { date: string; need_mm?: V | null }
interface Sec { status: 'ready' | 'fallback' | 'partial' | 'unavailable' | 'not_applicable'; reason?: string | null }
interface Alert { event?: string; headline?: string; severity?: string; ends?: string; area?: string; url?: string }
interface Access { date: string; status: 'ok' | 'marginal' | 'too_wet' | 'unknown'; why?: string[] }
interface Week {
  generated_at: string; label: string; forecast: Day[]; alerts: Alert[];
  forecast_source?: { provider: string; fallback: boolean; et0_method?: string } | null;
  irrigation: { verdict: string; kind: string; acre_in_per_acre?: V; field_acre_in?: V; days?: IrrDay[]; baseline?: { name: string } };
  field_access: { line: string; rule?: string; days: Access[]; wetness?: { percentile?: V; kind?: string; obs_date?: string } };
  sections: Record<string, Sec>;
}

const WD = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const wd = (iso: string) => WD[new Date(iso + 'T12:00:00Z').getUTCDay()];
const inch = (mm: number) => mm / 25.4;
const f1 = (n: number) => (n < 0.05 ? '0' : n < 10 ? n.toFixed(1) : String(Math.round(n)));
const degF = (c: number) => Math.round(c * 1.8 + 32);
const SHOW = (s?: Sec) => !!s && s.status !== 'unavailable' && s.status !== 'not_applicable';
const TAG = (s?: Sec) => (s?.status === 'fallback' ? 'From a backup forecast.' : s?.status === 'partial' ? 'Partly available.' : '');
const WORD = { ok: 'OK', marginal: 'Maybe', too_wet: 'Wet', unknown: '–' } as const;
const NAME = { ok: 'OK to work', marginal: 'Marginal', too_wet: 'Too wet', unknown: 'Unknown' } as const;
const SRC: Record<string, string> = { power: 'NASA POWER surface soil wetness', grace: 'NASA GRACE-DA surface soil wetness', smap_l4: 'NASA SMAP surface soil moisture' };
const ord = (n: number) => n + (n % 100 >= 11 && n % 100 <= 13 ? 'th' : ['th', 'st', 'nd', 'rd'][n % 10] ?? 'th');

export function ThisWeek({ loc }: { loc: Location }) {
  const sp = loc.spot;
  const st = useRoute<Week>(sp && sp.state !== 'ready' ? null : `/locations/${loc.id}/this_week`);
  const [pick, setPick] = useState<number | null>(null);
  if (st.kind === 'missing') return null;
  const w = st.kind === 'ok' ? st.data : null;
  return (
    <section className="tw" data-testid="this-week" aria-label="This week">
      <h3 className="tw-h">This week</h3>
      {st.kind === 'loading' && SKEL(3)}
      <RouteProblem st={st} what="The week ahead" reload={st.reload} />
      {w && <Body w={w} pick={pick} setPick={setPick} />}
    </section>
  );
}

function Body({ w, pick, setPick }: { w: Week; pick: number | null; setPick: (i: number | null) => void }) {
  const S = w.sections, irr = w.irrigation, acc = w.field_access;
  const showIrr = SHOW(S.irrigation), showAcc = SHOW(S.field_access) && acc.days.some((d) => d.status !== 'unknown');
  const showFc = SHOW(S.forecast) && w.forecast.length > 0;
  const showAl = SHOW(S.alerts) && w.alerts.length > 0;
  const gen = new Date(w.generated_at);
  const when = Number.isNaN(+gen) ? '' : gen.toLocaleString('en-US', { weekday: 'short', hour: 'numeric', minute: '2-digit' });
  const needs = (irr.days ?? []).map((d) => d.need_mm?.value ?? null);
  const strip = irr.kind === 'irrigate' && needs.some((n) => n != null);
  const peak = Math.max(0.1, ...needs.map((n) => n ?? 0));
  const acIn = irr.acre_in_per_acre?.value;
  const wet = acc.wetness?.percentile?.value;
  return (
    <div className="tw-body">
      <p className="tw-meta">{w.label}{when && <> · updated {when}</>}</p>
      {!showIrr && !showAcc && !showFc && !showAl && <p className="gap-line">{irr.verdict || 'The forecast is not available right now.'}</p>}

      {showIrr && (
        <div className="tw-block" data-testid="tw-irrigation">
          <p className="tw-verdict">{irr.verdict}</p>
          {irr.kind === 'irrigate' && acIn != null && <p className="tw-sub"><b>{acIn < 0.05 ? '0' : acIn.toFixed(1)}</b> acre-in/acre</p>}
          {strip && (
            <div className="tw-strip" role="img" aria-label={`Daily irrigation need: ${needs.map((n, i) => `${wd(irr.days![i].date)} ${f1(inch(n ?? 0))} in`).join(', ')}`}>
              {needs.map((n, i) => (
                <span key={i} className="tw-bar" title={`${wd(irr.days![i].date)}: ${f1(inch(n ?? 0))} in (${(n ?? 0).toFixed(1)} mm)`}>
                  <i><em style={{ '--h': Math.max(0.05, (n ?? 0) / peak), '--i': i } as React.CSSProperties} /></i>
                  <small>{wd(irr.days![i].date).slice(0, 2)}</small>
                </span>
              ))}
            </div>
          )}
          {TAG(S.irrigation) && <span className="tw-tag">{TAG(S.irrigation)}</span>}
        </div>
      )}

      {showAcc && (
        <div className="tw-block" data-testid="tw-access">
          <p className="tw-line">{acc.line}</p>
          <div className="tw-chips" role="group" aria-label="Field access by day">
            {acc.days.map((d, i) => (
              <button key={d.date} type="button" className={`tw-chip ${d.status} ${pick === i ? 'sel' : ''}`} aria-pressed={pick === i}
                title={`${wd(d.date)}: ${NAME[d.status]}${d.why?.length ? `. ${d.why.join(' ')}` : ''}`} onClick={() => setPick(pick === i ? null : i)}>
                <b>{wd(d.date)}</b><span>{WORD[d.status]}</span>
              </button>
            ))}
          </div>
          <p className="tw-why" aria-live="polite">{pick != null && <>{wd(acc.days[pick].date)}: {NAME[acc.days[pick].status]}.{acc.days[pick].why?.length ? ` ${acc.days[pick].why!.join(' ')}` : ' Nothing holds work back.'}</>}</p>
          {TAG(S.field_access) && <span className="tw-tag">{TAG(S.field_access)}</span>}
        </div>
      )}

      {showFc && (
        <div className="tw-block" data-testid="tw-forecast">
          <div className="tw-fc" role="table" aria-label="Seven-day forecast">
            {w.forecast.map((d) => {
              const r = d.rain_mm.value, hi = d.tmax_c.value, lo = d.tmin_c.value;
              return (
                <div key={d.date} className="tw-day" role="row" title={`${d.weekday}: rain ${r != null ? r.toFixed(1) : '–'} mm, high ${hi != null ? hi.toFixed(0) : '–'} °C, low ${lo != null ? lo.toFixed(0) : '–'} °C`}>
                  <b>{d.weekday}</b>
                  <span className="tw-rain">{r != null ? `${f1(inch(r))}"` : '–'}</span>
                  <span>{hi != null ? `${degF(hi)}°` : '–'}</span>
                  <span className="muted">{lo != null ? `${degF(lo)}°` : '–'}</span>
                  <small className="d-only">{r != null ? `${r.toFixed(0)} mm` : ''}</small>
                  <small className="d-only">{hi != null && lo != null ? `${hi.toFixed(0)}/${lo.toFixed(0)}°C` : ''}</small>
                </div>
              );
            })}
          </div>
          <p className="tw-key">Rain in inches, high and low in °F. Hover or detail for mm and °C.{TAG(S.forecast) ? ` ${TAG(S.forecast)}` : ''}</p>
        </div>
      )}

      {showAl && (
        <ul className="tw-alerts" data-testid="tw-alerts">
          {w.alerts.map((a, i) => (
            <li key={i}><span>{a.event ?? a.headline ?? 'Weather alert'}{a.area ? ` · ${a.area.split(';')[0]}` : ''}</span>
              <a href={a.url?.startsWith('http') ? a.url : 'https://www.weather.gov/'} target="_blank" rel="noreferrer">National Weather Service</a></li>
          ))}
        </ul>
      )}

      <details className="tw-more" data-testid="tw-more">
        <summary>More detail</summary>
        <div className="tw-more-in">
          {showAcc && acc.rule && <p><b>How access is judged.</b> {acc.rule}</p>}
          {showAcc && wet != null && <p><b>Soil wetness.</b> {ord(Math.round(wet))} percentile for this place and time of year{acc.wetness?.kind ? `, from ${SRC[acc.wetness.kind] ?? acc.wetness.kind}` : ''}{acc.wetness?.obs_date ? `, read ${acc.wetness.obs_date}` : ''}.</p>}
          {showFc && <p><b>Forecast from.</b> {w.forecast_source?.provider === 'nws' ? 'US National Weather Service' : 'Open-Meteo'}{w.forecast_source?.fallback ? ' (backup source)' : ''}.{w.forecast_source?.et0_method ? ` Water use of the air: ${w.forecast_source.et0_method}.` : ''}</p>}
          {showIrr && irr.baseline?.name && <p><b>Irrigation need.</b> For {irr.baseline.name.toLowerCase()}, with 80% of the rain counted.{irr.field_acre_in?.value != null ? ` About ${Math.round(irr.field_acre_in.value)} acre-in over the whole field.` : ''}</p>}
        </div>
      </details>
    </div>
  );
}
