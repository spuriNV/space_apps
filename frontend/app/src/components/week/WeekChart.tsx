// Seven-day visual for "This week": rain bars + crop water use dots, temperature range ticks, field-access dots,
// and an irrigation gauge. Pure SVG + CSS transitions; values come from GET /locations/{id}/this_week.
import { useEffect, useState } from 'react';
import { useCountUp } from './useCountUp';
import './weekchart.css';
import { ChartTable } from '../a11y/ChartTable';
import { t } from '../../i18n';

interface V { value: number | null }
export interface WcDay { date: string; rain_mm: V; tmax_c: V; tmin_c: V; et0_mm?: V }
export interface WcIrrDay { kc?: V | null; need_mm?: V | null }
export interface WcAccess { date: string; status: 'ok' | 'marginal' | 'too_wet' | 'unknown' }
interface Props {
  forecast: WcDay[]; irrDays?: WcIrrDay[]; access?: WcAccess[]; verdict: string; needIn: number | null; showGauge: boolean;
}

const INIT = [t('week.in0'), t('week.in1'), t('week.in2'), t('week.in3'), t('week.in4'), t('week.in5'), t('week.in6')];
const WD = [t('week.wd0'), t('week.wd1'), t('week.wd2'), t('week.wd3'), t('week.wd4'), t('week.wd5'), t('week.wd6')];
const dow = (iso: string) => new Date(iso + 'T12:00:00Z').getUTCDay();
const inch = (mm: number) => mm / 25.4;
const degF = (c: number) => Math.round(c * 1.8 + 32);
const ACC = { ok: t('week.nameOk'), marginal: t('week.nameMarginal'), too_wet: t('week.nameWet'), unknown: t('week.noReading') } as const;
const W = 48, RAIN_H = 64, T0 = 78, T1 = 116, DOT_Y = 130, LAB_Y = 152, H = 160;
const GAUGE_MAX_IN = 3;

function Gauge({ inches, verdict }: { inches: number | null; verdict: string }) {
  const v = useCountUp(inches ?? 0);
  const R = 30, C = Math.PI * R; // half circle
  const frac = Math.min(1, (inches ?? 0) / GAUGE_MAX_IN);
  const [on, setOn] = useState(false);
  useEffect(() => { const r = requestAnimationFrame(() => setOn(true)); return () => cancelAnimationFrame(r); }, []);
  return (
    <div className="wc-gauge">
      <svg viewBox="0 0 80 48" width="84" height="50" role="img" aria-label={inches != null ? t('week.gaugeAria', { n: inches.toFixed(1) }) : t('week.noIrr')}>
        <path d="M10 42 A30 30 0 0 1 70 42" className="wc-g-track" pathLength={C} />
        <path d="M10 42 A30 30 0 0 1 70 42" className="wc-g-fill" pathLength={C} strokeDasharray={C} strokeDashoffset={on ? C * (1 - frac) : C} />
        <text x="40" y="40" textAnchor="middle" className="wc-g-num">{v.toFixed(1)}</text>
      </svg>
      <div className="wc-g-txt"><span className="wc-g-unit">{t('week.inThisWeek')}</span><b>{verdict}</b></div>
    </div>
  );
}

export function WeekChart({ forecast, irrDays, access, verdict, needIn, showGauge }: Props) {
  const [on, setOn] = useState(false);
  const [tip, setTip] = useState<number | null>(null);
  useEffect(() => { const r = requestAnimationFrame(() => setOn(true)); return () => cancelAnimationFrame(r); }, []);
  const n = Math.min(7, forecast.length);
  const days = forecast.slice(0, n);
  const use = days.map((d, i) => { const kc = irrDays?.[i]?.kc?.value, et = d.et0_mm?.value; return kc != null && et != null ? kc * et : null; });
  const rains = days.map((d) => d.rain_mm.value ?? 0);
  const top = Math.max(5, ...rains, ...use.map((u) => u ?? 0));
  const ys = (mm: number) => (mm / top) * RAIN_H;
  const temps = days.flatMap((d) => [d.tmax_c.value, d.tmin_c.value]).filter((t): t is number => t != null);
  const tLo = Math.min(...temps), tHi = Math.max(...temps);
  const ty = (t: number) => T1 - ((t - tLo) / Math.max(1, tHi - tLo)) * (T1 - T0);
  const hasUse = use.some((u) => u != null);
  const hasAcc = !!access && access.some((a) => a.status !== 'unknown');
  const usePts = use.map((u, i) => (u == null ? null : [i * W + W / 2, RAIN_H - ys(u)] as const));
  const tipFor = (i: number) => {
    const d = days[i], a = access?.[i];
    const r = d.rain_mm.value, hi = d.tmax_c.value, lo = d.tmin_c.value;
    return [`${WD[dow(d.date)]}`, r != null ? t('week.tipRain', { n: inch(r).toFixed(2) }) : null, use[i] != null ? t('week.tipUse', { n: inch(use[i]!).toFixed(2) }) : null,
      hi != null && lo != null ? `${degF(lo)}–${degF(hi)} °F` : null, a && hasAcc ? ACC[a.status] : null].filter(Boolean).join(' · ');
  };
  const rainTot = rains.reduce((a, b) => a + b, 0);
  const hiF = days.map((d) => d.tmax_c.value).filter((x): x is number => x != null).map(degF), loF = days.map((d) => d.tmin_c.value).filter((x): x is number => x != null).map(degF);
  const summary = t('week.summary', { n }) + ' ' + (rainTot < 0.5 ? t('week.noRain') : t('week.rainTotal', { n: inch(rainTot).toFixed(1) })) + (hiF.length ? t('week.highs', { a: Math.min(...hiF), b: Math.max(...hiF) }) : '') + (hasAcc ? t('week.okDays', { k: access!.filter((a) => a.status === 'ok').length, n }) : '') + '.';
  return (
    <div className="wc" data-testid="week-chart">
      {showGauge && <Gauge inches={needIn} verdict={verdict} />}
      <svg viewBox={`0 0 ${n * W} ${H}`} className={`wc-svg ${on ? 'on' : ''}`} role="group" aria-label={summary}>
        <line x1="0" x2={n * W} y1={RAIN_H} y2={RAIN_H} className="wc-base" />
        {days.map((d, i) => (
          <rect key={d.date} className="wc-rain" x={i * W + 13} width={22} y={RAIN_H - Math.max(rains[i] > 0 ? 2 : 0, ys(rains[i]))} height={Math.max(rains[i] > 0 ? 2 : 0, ys(rains[i]))} rx="3"
            style={{ transitionDelay: `${i * 60}ms` }} />
        ))}
        {hasUse && (
          <>
            <polyline className="wc-use-line" points={usePts.filter(Boolean).map((p) => p!.join(',')).join(' ')} />
            {usePts.map((p, i) => p && <circle key={i} className="wc-use" cx={p[0]} cy={p[1]} r="4" style={{ transitionDelay: `${240 + i * 60}ms` }} />)}
          </>
        )}
        {days.map((d, i) => {
          const hi = d.tmax_c.value, lo = d.tmin_c.value;
          if (hi == null || lo == null) return null;
          return <line key={d.date} className="wc-temp" x1={i * W + W / 2} x2={i * W + W / 2} y1={ty(hi)} y2={ty(lo) + 0.01} style={{ transitionDelay: `${i * 60}ms` }} />;
        })}
        {hasAcc && days.map((d, i) => { const st = access![i]?.status ?? 'unknown'; return (
          <g key={d.date} className={`wc-acc ${st}`} style={{ transitionDelay: `${i * 60}ms` }} aria-hidden="true">
            <circle cx={i * W + W / 2} cy={DOT_Y} r="9" />
            <text x={i * W + W / 2} y={DOT_Y + 4.5} textAnchor="middle" className="wc-acc-g">{st === 'ok' ? '✓' : st === 'marginal' ? '~' : st === 'too_wet' ? '✕' : ''}</text>
          </g>); })}
        {days.map((d, i) => (
          <text key={d.date} x={i * W + W / 2} y={LAB_Y} textAnchor="middle" className={`wc-day ${tip === i ? 'sel' : ''}`}>{INIT[dow(d.date)]}</text>
        ))}
        {days.map((d, i) => (
          <g key={d.date} role="button" tabIndex={0} aria-label={tipFor(i)} className="wc-hit" onMouseEnter={() => setTip(i)} onMouseLeave={() => setTip(null)}
            onFocus={() => setTip(i)} onBlur={() => setTip(null)} onClick={() => setTip(tip === i ? null : i)}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setTip(tip === i ? null : i); } }}>
            <rect x={i * W} y="0" width={W} height={H} className={`wc-col ${tip === i ? 'sel' : ''}`} rx="8" />
          </g>
        ))}
      </svg>
      <ChartTable caption={t('week.tblCaption')} head={[t('week.tblDay'), t('week.tblRain'), t('week.tblUse'), t('week.tblTemp'), t('week.tblAccess')]}
        rows={days.map((d, i) => { const hi = d.tmax_c.value, lo = d.tmin_c.value; return [WD[dow(d.date)], d.rain_mm.value != null ? inch(d.rain_mm.value).toFixed(2) : '–', use[i] != null ? inch(use[i]!).toFixed(2) : '–', hi != null && lo != null ? `${degF(lo)}–${degF(hi)}` : '–', access?.[i] && hasAcc ? ACC[access[i].status] : '–']; })} />
      <div className="wc-tip" role="status" aria-live="polite">{tip != null ? tipFor(tip) : <>
        <span className="wc-k"><i className="k-rain" />{t('week.kRain')}</span>{hasUse && <span className="wc-k"><i className="k-use" />{t('week.kUse')}</span>}
        <span className="wc-k"><i className="k-temp" />{t('week.kTemp')}</span>{hasAcc && <span className="wc-k"><i className="k-ok">✓</i>{t('week.kOk')} <i className="k-mid">~</i>{t('week.kMaybe')} <i className="k-wet">✕</i>{t('week.kWet')}</span>}</>}</div>
    </div>
  );
}
