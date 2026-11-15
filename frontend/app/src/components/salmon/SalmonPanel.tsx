// "Salmon and the field" (BC field only). GET /api/locations/<id>/salmon: the Salmon River gauge, water temperature, when the
// fish are in the river, and how much water this field's rotations would take in the same weeks.
// Farmer default: a plain summary and the respect text. One local "More detail" opens the charts and tables.
// Charts are inline SVG drawn at the panel's real pixel width, so a 13px axis label stays 13px on a phone.
import { useEffect, useMemo, useRef, useState, type PointerEvent as RPE } from 'react';
import { API_BASE } from '../../api';
import Icon from '../Icons';
import { Seg } from '../ui/Seg';
import './salmon.css';

// ---------- API shape (only the parts used here) ----------
interface Src { id?: string; title: string; url: string }
interface Num { value: number; unit?: string; low?: number; high?: number; note?: string; source?: Src }
interface Threshold { id: string; kind: 'official' | 'policy_rule' | 'our_reference'; label: string; value: Num; applies?: { from: string; to: string } }
interface FlowDay { date: string; discharge_m3s: number; approval?: string; p10?: number; p50?: number }
interface OrderEvent { date: string; kind: string; title: string; url?: string }
interface OrderYear { year: number; orders: OrderEvent[]; data_status: string; aug_mean: Num; aug_mean_pct_of_normal: Num; aug_rank_lowest: Num }
interface TempDay { date: string; mean_c: number | null; max_c: number | null }
interface TempStation { station: string; name: string; role: string; daily: TempDay[]; summers: { year: number; days_max_ge_18: Num; days_max_ge_20: Num; peak: Num }[] }
interface TempRule { id: string; label: string; value: Num }
interface Species { species: string; common: string; stage: string; months: number[]; scope: string; verified: boolean }
interface Indicator { indicator: string; label: string; spearman_r: Num; hit_rate: Num; driest_third_years: number[]; driest_third_with_low_august: number[]; pct_rank_2026?: Num; n_years: number }
interface EWRow { year: number; aug_mean_m3s: number | null; snow_late_apr_frac: number | null; eccc_nov_mar_precip_mm: number | null }
interface WaterItem { strategy_id: string; short_name: string; irrigated_in_window: boolean; draw_aug_sep_m3: Num; draw_rate_l_s: Num; share_of_low_aug_flow_pct: Num }
interface ScaleRow { licences: Num; assumed_ha_per_licence: Num; draw_rate_l_s: Num; share_of_low_aug_flow_pct: Num }
export interface Salmon {
  river: string; summary: string[];
  series_meta: { flow_daily: { station: string; approved_to: string; provisional_from?: string } };
  flow: {
    latest?: { discharge: Num }; thresholds: Threshold[]; threshold_note?: string;
    percentiles_by_doy: { doy: number; p10: number; p50: number; p90: number }[]; daily: FlowDay[]; order_years: OrderYear[];
  };
  temperature: { thresholds: TempRule[]; stations: TempStation[]; satellite: { reason: string } };
  run_timing: { species: Species[]; irrigation_months: number[]; critical_window: { from: string; to: string } };
  early_warning: { label: string; note?: string; indicators: Indicator[]; table: EWRow[] };
  water_for_salmon: { reference_low_flow: Num; items: WaterItem[]; scale_up: { label: string; rows: ScaleRow[]; note?: string } };
  respect: { statements: string[]; links: { title: string; url: string }[] };
}

// ---------- small helpers ----------
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const DAY = 864e5;
const tOf = (s: string) => { const [y, m, d] = s.split('-').map(Number); return Date.UTC(y, m - 1, d) / DAY; };
const dOf = (t: number) => new Date(t * DAY);
const label = (t: number) => `${MON[dOf(t).getUTCMonth()]} ${dOf(t).getUTCDate()}`;
const doyOf = (t: number) => Math.min(365, Math.round(t - Date.UTC(dOf(t).getUTCFullYear(), 0, 1) / DAY) + 1);
const CFS = 35.3147;
const cfs = (m3s: number) => Math.round(m3s * CFS);
const f2 = (n: number) => (n >= 10 ? n.toFixed(1) : n.toFixed(2));
const num = (n: number) => Math.round(n).toLocaleString('en-CA');
const clamp = (x: number, a: number, b: number) => Math.min(b, Math.max(a, x));

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [w, setW] = useState(0);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    const set = () => setW(Math.round(el.getBoundingClientRect().width));
    set();
    const ro = new ResizeObserver(set); ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, w] as const;
}

const FLOW_COL = '#3d97e8';    // water (data colour)
const TEMP_COL = '#c2571a';
const FISH_COL = '#b8412c';

// ---------- flow chart ----------
const FLOW_MAX = 3;
const THRESH_NAME: Record<string, string> = {
  order_2026_m311: '2026 order trigger', order_2023_m238: '2023 order trigger',
  mad_20pct: '20% of average flow', mad_10pct: '10% of average flow', mad_5pct: '5% of average flow', aug_p10_reference: 'Low August, 1 year in 10',
};
const parenOf = (l: string) => /\(([^)]*)\)/.exec(l)?.[1]?.split(';')[0] ?? '';
function Swatch({ kind }: { kind: Threshold['kind'] }) {
  const p = kind === 'official' ? { stroke: 'var(--bad)', strokeWidth: 2.5 } : kind === 'policy_rule' ? { stroke: 'var(--warn)', strokeWidth: 2, strokeDasharray: '6 4' } : { stroke: 'var(--text-2)', strokeWidth: 2.5, strokeDasharray: '1 4', strokeLinecap: 'round' as const };
  return <svg width="30" height="12" aria-hidden="true"><line x1="1" y1="6" x2="29" y2="6" {...p} /></svg>;
}

function FlowChart({ s }: { s: Salmon }) {
  const years = s.flow.order_years.map((o) => o.year).sort((a, b) => b - a);
  const [year, setYear] = useState(years[0]);
  const [box, W] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);
  const oy = s.flow.order_years.find((o) => o.year === year)!;
  const t0 = tOf(`${year}-07-15`), t1 = tOf(`${year}-11-15`);
  const H = 230, ml = 30, mr = 10, mt = 22, mb = 26;
  const pw = Math.max(10, W - ml - mr), ph = H - mt - mb;
  const X = (t: number) => ml + ((t - t0) / (t1 - t0)) * pw;
  const Y = (v: number) => mt + (1 - v / FLOW_MAX) * ph;
  const rows = useMemo(() => s.flow.daily.filter((d) => d.date.startsWith(String(year)) && tOf(d.date) >= t0 && tOf(d.date) <= t1), [s, year, t0, t1]);
  const band = useMemo(() => {
    const up: string[] = [], dn: string[] = [];
    for (let t = t0; t <= t1; t++) { const p = s.flow.percentiles_by_doy[doyOf(t) - 1]; if (!p) continue; up.push(`${X(t).toFixed(1)},${Y(p.p90).toFixed(1)}`); dn.push(`${X(t).toFixed(1)},${Y(p.p10).toFixed(1)}`); }
    return `M${up.join('L')}L${dn.reverse().join('L')}Z`;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [s, t0, t1, W]);
  const segs = useMemo(() => {
    const out: { prov: boolean; pts: string[] }[] = [];
    for (const d of rows) {
      const prov = d.approval !== 'approved';
      let cur = out[out.length - 1];
      if (!cur || cur.prov !== prov) { cur = { prov, pts: cur ? [cur.pts[cur.pts.length - 1]] : [] }; out.push(cur); }
      cur.pts.push(`${X(tOf(d.date)).toFixed(1)},${Y(d.discharge_m3s).toFixed(1)}`);
    }
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, W]);
  const thresholds = s.flow.thresholds;
  const last = rows[rows.length - 1];
  const isNow = !!last && last.approval !== 'approved' && tOf(last.date) >= t1 - 3;
  const nowV = s.flow.latest?.discharge.value ?? last?.discharge_m3s;
  const provStart = rows.find((d) => d.approval !== 'approved');
  const hd = hover != null ? rows.find((d) => tOf(d.date) === hover) : null;
  const move = (e: RPE<SVGSVGElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    const t = Math.round(t0 + ((e.clientX - r.left - ml) / pw) * (t1 - t0));
    setHover(t >= t0 && t <= t1 ? t : null);
  };
  const pick = (d: FlowDay) => {
    const pp = s.flow.percentiles_by_doy[doyOf(tOf(d.date)) - 1];
    return <>{label(tOf(d.date))}: <b>{f2(d.discharge_m3s)} m³/s</b> ({cfs(d.discharge_m3s)} cfs){pp ? <>. Normal for the day: {f2(pp.p50)} m³/s.</> : null}{d.approval !== 'approved' && ' Provisional.'}</>;
  };
  const crit = s.run_timing.critical_window;
  const cx0 = X(tOf(`${year}-${crit.from}`)), cx1 = X(tOf(`${year}-${crit.to}`) + 1);
  const ticks = [`${year}-08-01`, `${year}-09-01`, `${year}-10-01`, `${year}-11-01`].map(tOf);
  const groups: { name: string; kind: Threshold['kind'] }[] = [
    { name: 'Orders (BC)', kind: 'official' }, { name: 'Drought-plan rules (BC)', kind: 'policy_rule' }, { name: 'Our reference', kind: 'our_reference' },
  ];
  const ord = (e: OrderEvent) => (e.kind === 'rescission' ? 'Order lifted' : 'Order');
  return (
    <div className="sp-block" data-testid="salmon-flow">
      <div className="sp-head">
        <h3>How low is the river?</h3>
        <Seg label="Year" value={year} options={years.map((y) => ({ v: y, label: String(y) }))} onChange={(v) => { setYear(v); setHover(null); }} className="small" testid="salmon-year" />
      </div>
      <p className="sp-lede">August {year} averaged <b title={`${f2(oy.aug_mean.value)} m³/s = ${cfs(oy.aug_mean.value)} cfs`}>{f2(oy.aug_mean.value)} m³/s</b>, {Math.round(oy.aug_mean_pct_of_normal.value)}% of a normal August. {rankLine(oy)}</p>
      <div className="sp-read" aria-live="off">{hd ? pick(hd) : <span className="muted">Tap or hover the chart for one day. Flow in m³/s (1 m³/s = {cfs(1)} cfs).</span>}</div>
      <div ref={box} className="sp-chart">
        {W > 0 && (
          <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Salmon River flow, ${year}, July 15 to November 15, with the order trigger levels`}
            onPointerMove={move} onPointerDown={move} onPointerLeave={() => setHover(null)} style={{ touchAction: 'pan-y' }}>
            <defs>
              <clipPath id="sp-clip"><rect x={ml} y={mt} width={pw} height={ph} /></clipPath>
              <pattern id="sp-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)"><line x1="0" y1="0" x2="0" y2="6" stroke="var(--muted)" strokeWidth="2" /></pattern>
            </defs>
            <rect x={cx0} y={mt} width={Math.max(0, cx1 - cx0)} height={ph} fill="var(--warn)" opacity="0.07" />
            {[0, 1, 2, 3].map((v) => <g key={v}><line x1={ml} x2={W - mr} y1={Y(v)} y2={Y(v)} stroke="var(--line)" /><text x={ml - 6} y={Y(v) + 4} textAnchor="end">{v}</text></g>)}
            {ticks.map((t) => <text key={t} x={X(t)} y={H - 6} textAnchor="middle">{MON[dOf(t).getUTCMonth()]}</text>)}
            <g clipPath="url(#sp-clip)">
              <path d={band} fill={FLOW_COL} opacity="0.16"><title>Usual range for the day: the middle 80% of days, 1991 to 2020</title></path>
              {thresholds.map((t) => {
                const mine = t.kind !== 'official' || t.id.includes(String(year));
                const st = t.kind === 'official' ? { stroke: 'var(--bad)', strokeWidth: 2.5 } : t.kind === 'policy_rule' ? { stroke: 'var(--warn)', strokeWidth: 1.75, strokeDasharray: '7 4' } : { stroke: 'var(--text-2)', strokeWidth: 2.25, strokeDasharray: '1 4', strokeLinecap: 'round' as const };
                return <line key={t.id} x1={ml} x2={W - mr} y1={Y(t.value.value)} y2={Y(t.value.value)} {...st} opacity={mine ? 1 : 0.3}><title>{`${THRESH_NAME[t.id] ?? t.label}: ${f2(t.value.value)} m³/s (${cfs(t.value.value)} cfs)`}</title></line>;
              })}
              {segs.map((g, i) => <polyline key={i} points={g.pts.join(' ')} fill="none" stroke={FLOW_COL} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" opacity={g.prov ? 0.85 : 1} style={{ filter: 'brightness(0.78)' }} />)}
            </g>
            {provStart && <rect x={X(tOf(provStart.date))} y={H - mb} width={Math.max(0, X(t1) - X(tOf(provStart.date)))} height="4" fill="url(#sp-hatch)" opacity="0.8"><title>Provisional readings: Water Survey of Canada may still revise them</title></rect>}
            {oy.orders.map((e) => {
              const x = X(tOf(e.date)); const lifted = e.kind === 'rescission';
              return <g key={e.date + e.kind}><line x1={x} x2={x} y1={mt - 4} y2={mt + ph} stroke="var(--text)" strokeWidth="1" opacity="0.35" />
                {lifted ? <circle cx={x} cy={mt - 10} r="5" fill="var(--panel)" stroke="var(--text)" strokeWidth="2" /> : <path d={`M${x - 6},${mt - 15}L${x + 6},${mt - 15}L${x},${mt - 4}Z`} fill="var(--text)" />}
                <title>{`${label(tOf(e.date))}: ${e.title}`}</title></g>;
            })}
            {hover != null && <line x1={X(hover)} x2={X(hover)} y1={mt} y2={mt + ph} stroke="var(--text)" strokeWidth="1" />}
            {hd && <circle cx={X(hover!)} cy={clamp(Y(hd.discharge_m3s), mt, mt + ph)} r="4.5" fill="var(--panel)" stroke="var(--text)" strokeWidth="2" />}
            {isNow && last && nowV != null && (() => {
              const x = X(tOf(last.date)), y = Y(nowV); const bw = 88, bx = Math.min(x + 4, W - mr) - bw;
              return <g data-testid="salmon-now"><circle cx={x} cy={y} r="5" fill="var(--panel)" stroke={FLOW_COL} strokeWidth="2.5" style={{ filter: 'brightness(0.78)' }} />
                <line x1={x} x2={x} y1={y - 6} y2={y - 22} stroke="var(--text)" strokeWidth="1" />
                <rect x={bx} y={y - 44} width={bw} height="22" rx="11" fill="var(--text)" /><text x={bx + bw / 2} y={y - 29} textAnchor="middle" fill="var(--panel)" style={{ fill: 'var(--panel)', fontWeight: 600 }}>Now {f2(nowV)}</text></g>;
            })()}
          </svg>
        )}
      </div>
      <ul className="sp-key">
        <li><i className="sp-sw band" /> Usual range for the day (most years)</li>
        <li><i className="sp-sw crit" /> Aug and Sep, the critical weeks</li>
        {oy.orders.length > 0 && <li><svg width="30" height="14" aria-hidden="true"><path d="M9,2L21,2L15,12Z" fill="var(--text)" /></svg> Order issued <span className="sp-sp" /><svg width="14" height="14" aria-hidden="true"><circle cx="7" cy="7" r="5" fill="var(--panel)" stroke="var(--text)" strokeWidth="2" /></svg> lifted</li>}
        {provStart && <li><i className="sp-sw hatch" /> Provisional: may be revised</li>}
      </ul>
      {groups.map((g) => (
        <div key={g.kind} className="sp-tgroup">
          <h4>{g.name}</h4>
          {thresholds.filter((t) => t.kind === g.kind).map((t) => (
            <div key={t.id} className="sp-trow" title={t.label}><Swatch kind={t.kind} /><span>{THRESH_NAME[t.id] ?? t.label}{parenOf(t.label) && g.kind === 'policy_rule' ? <small>, {parenOf(t.label)}</small> : null}</span><b title={`${cfs(t.value.value)} cfs`}>{f2(t.value.value)} m³/s</b></div>
          ))}
        </div>
      ))}
      {oy.orders.length > 0 && <ul className="sp-orders">{oy.orders.map((e) => <li key={e.date + e.kind}><b>{label(tOf(e.date))}</b> <span>{ord(e)}. {e.title}{e.url && <> <a href={e.url} target="_blank" rel="noreferrer">Source</a></>}</span></li>)}</ul>}
      {s.flow.threshold_note && <p className="sp-note">{s.flow.threshold_note}</p>}
      <cite className="sp-cite">Water Survey of Canada gauge {s.series_meta.flow_daily.station}, {s.river.split(',')[0].replace(/ \(.*\)/, '')} near Salmon Arm. Checked readings to {fullDate(s.series_meta.flow_daily.approved_to)}, provisional after. Chart cut off at {FLOW_MAX} m³/s.</cite>
    </div>
  );
}
const fullDate = (d: string) => `${dOf(tOf(d)).getUTCDate()} ${MON[dOf(tOf(d)).getUTCMonth()]} ${d.slice(0, 4)}`;
const ordinal = (n: number) => (n === 2 ? '2nd' : n === 3 ? '3rd' : `${n}th`);
const rankLine = (o: OrderYear) => {
  const n = o.aug_rank_lowest.value, of = /among (\d+)/.exec(o.aug_rank_lowest.note ?? '')?.[1];
  return `${n === 1 ? 'The lowest' : `The ${ordinal(n)} lowest`} of ${of ?? 'all'} Augusts on record.`;
};

// ---------- temperature ----------
const T_MAX = 28;
function TempChart({ s }: { s: Salmon }) {
  const stations = s.temperature.stations;
  const [st, setSt] = useState(stations[0].station);
  const years = useMemo(() => [...new Set(stations[0].summers.map((x) => x.year))].sort((a, b) => b - a), [stations]);
  const [year, setYear] = useState(years[0]);
  const [hover, setHover] = useState<number | null>(null);
  const [box, W] = useWidth<HTMLDivElement>();
  const station = stations.find((x) => x.station === st)!;
  const sum = station.summers.find((x) => x.year === year);
  const t0 = tOf(`${year}-06-01`), t1 = tOf(`${year}-10-31`);
  const H = 200, ml = 30, mr = 10, mt = 10, mb = 26;
  const pw = Math.max(10, W - ml - mr), ph = H - mt - mb;
  const X = (t: number) => ml + ((t - t0) / (t1 - t0)) * pw;
  const Y = (v: number) => mt + (1 - v / T_MAX) * ph;
  const rows = station.daily.filter((d) => tOf(d.date) >= t0 && tOf(d.date) <= t1);
  const path = (k: 'max_c' | 'mean_c') => {
    let out = '', pen = false;
    for (const d of rows) { const v = d[k]; if (v == null) { pen = false; continue; } out += `${pen ? 'L' : 'M'}${X(tOf(d.date)).toFixed(1)},${Y(v).toFixed(1)}`; pen = true; }
    return out;
  };
  const r18 = s.temperature.thresholds.find((t) => t.id === 't18'), r20 = s.temperature.thresholds.find((t) => t.id === 't20');
  const hd = hover != null ? rows.find((d) => tOf(d.date) === hover) : null;
  const move = (e: RPE<SVGSVGElement>) => { const r = e.currentTarget.getBoundingClientRect(); const t = Math.round(t0 + ((e.clientX - r.left - ml) / pw) * (t1 - t0)); setHover(t >= t0 && t <= t1 ? t : null); };
  const ticks = [`${year}-06-01`, `${year}-07-01`, `${year}-08-01`, `${year}-09-01`, `${year}-10-01`].map(tOf);
  const why = (r?: TempRule) => (r ? r.label.split(': ')[1]?.split(';')[0] : '');
  const rule = (r?: TempRule) => r?.value.source?.url;
  return (
    <div className="sp-block" data-testid="salmon-temp">
      <div className="sp-head">
        <h3>How warm is the water?</h3>
        <Seg label="Year" value={year} options={years.map((y) => ({ v: y, label: String(y) }))} onChange={(v) => { setYear(v); setHover(null); }} className="small" />
      </div>
      <Seg label="Gauge" value={st} options={stations.map((x) => ({ v: x.station, label: x.role.startsWith('lower') ? 'Lower river' : 'Upper river', title: `${x.name}, gauge ${x.station}` }))} onChange={setSt} className="small sp-seg2" />
      {sum && <p className="sp-lede">Water reached <b>{sum.peak.value.toFixed(1)} °C</b>. It topped 18 °C on {sum.days_max_ge_18.value} days and 20 °C on {sum.days_max_ge_20.value} days (June to September).</p>}
      <div className="sp-read">{hd ? <>{label(tOf(hd.date))}: <b>{hd.max_c != null ? `${hd.max_c.toFixed(1)} °C` : 'no reading'}</b> at the warmest{hd.mean_c != null && <>, {hd.mean_c.toFixed(1)} °C on average</>}.</> : <span className="muted">Tap or hover the chart for one day. Water temperature in °C.</span>}</div>
      <div ref={box} className="sp-chart">
        {W > 0 && (
          <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Water temperature, ${year}, with the 18 and 20 degree lines`} onPointerMove={move} onPointerDown={move} onPointerLeave={() => setHover(null)} style={{ touchAction: 'pan-y' }}>
            {[0, 10, 20].map((v) => <g key={v}><line x1={ml} x2={W - mr} y1={Y(v)} y2={Y(v)} stroke="var(--line)" /><text x={ml - 6} y={Y(v) + 4} textAnchor="end">{v}</text></g>)}
            {ticks.map((t) => <text key={t} x={X(t) + 14} y={H - 6} textAnchor="middle">{MON[dOf(t).getUTCMonth()]}</text>)}
            {r18 && <g><line x1={ml} x2={W - mr} y1={Y(18)} y2={Y(18)} stroke="var(--warn)" strokeWidth="1.75" strokeDasharray="7 4" /><text x={W - mr - 2} y={Y(18) + 15} textAnchor="end" style={{ fill: 'var(--warn)', fontWeight: 600 }}>18 °C</text></g>}
            {r20 && <g><line x1={ml} x2={W - mr} y1={Y(20)} y2={Y(20)} stroke="var(--bad)" strokeWidth="2.5" /><text x={W - mr - 2} y={Y(20) - 5} textAnchor="end" style={{ fill: 'var(--bad)', fontWeight: 600 }}>20 °C</text></g>}
            <path d={path('mean_c')} fill="none" stroke={TEMP_COL} strokeWidth="1.5" opacity="0.5" strokeLinejoin="round" />
            <path d={path('max_c')} fill="none" stroke={TEMP_COL} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" style={{ filter: 'brightness(0.9)' }} />
            {hover != null && <line x1={X(hover)} x2={X(hover)} y1={mt} y2={mt + ph} stroke="var(--text)" strokeWidth="1" />}
            {hd?.max_c != null && <circle cx={X(hover!)} cy={Y(hd.max_c)} r="4.5" fill="var(--panel)" stroke="var(--text)" strokeWidth="2" />}
          </svg>
        )}
      </div>
      <ul className="sp-key">
        <li><svg width="30" height="12" aria-hidden="true"><line x1="1" y1="6" x2="29" y2="6" stroke={TEMP_COL} strokeWidth="2.5" /></svg> Warmest of each day</li>
        <li><svg width="30" height="12" aria-hidden="true"><line x1="1" y1="6" x2="29" y2="6" stroke={TEMP_COL} strokeWidth="1.5" opacity="0.5" /></svg> Average of each day</li>
      </ul>
      <div className="sp-tgroup">
        {r18 && <div className="sp-trow"><svg width="30" height="12" aria-hidden="true"><line x1="1" y1="6" x2="29" y2="6" stroke="var(--warn)" strokeWidth="2" strokeDasharray="6 4" /></svg><span>18 °C <small>, {why(r18)}</small></span></div>}
        {r20 && <div className="sp-trow"><svg width="30" height="12" aria-hidden="true"><line x1="1" y1="6" x2="29" y2="6" stroke="var(--bad)" strokeWidth="2.5" /></svg><span>20 °C <small>, {why(r20)}</small></span></div>}
      </div>
      <details className="sp-why"><summary>Why no satellite temperature?</summary><p>{s.temperature.satellite.reason}</p></details>
      <cite className="sp-cite">Water Survey of Canada gauges {stations.map((x) => x.station).join(' and ')}, provisional, recorded since May 2025. Rules: DFO Fraser River Environmental Watch{rule(r20) && <> (<a href={rule(r20)} target="_blank" rel="noreferrer">report</a>)</>} and the BC water quality guideline.</cite>
    </div>
  );
}

// ---------- run timing ----------
const rowName = (sp: Species) => {
  const n = sp.species[0].toUpperCase() + sp.species.slice(1);
  return sp.stage.startsWith('adults enter') || sp.stage.startsWith('adults arrive') ? `${n} arrive` : sp.stage.startsWith('spawn') ? `${n} spawn` : n;
};
function RunTiming({ s }: { s: Salmon }) {
  const rt = s.run_timing;
  const rows = rt.species.filter((x) => x.months.length < 12);
  const irr = new Set(rt.irrigation_months);
  const cw = [Number(rt.critical_window.from.slice(0, 2)), Number(rt.critical_window.to.slice(0, 2))];
  return (
    <div className="sp-block" data-testid="salmon-timing">
      <div className="sp-head"><h3>When are the fish in the river?</h3></div>
      <div className="sp-strip" role="table" aria-label="Months when salmon are in the Salmon River and when the field is irrigated">
        <div className="sp-srow sp-shead" role="row"><span className="sp-slab" />{MON.map((m, i) => <span key={m} role="columnheader" aria-label={m} className={`sp-cell ${irr.has(i + 1) ? 'irr' : ''} ${i + 1 >= cw[0] && i + 1 <= cw[1] ? 'crit' : ''}`}>{m[0]}</span>)}</div>
        <div className="sp-srow" role="row"><span className="sp-slab">Field irrigated</span>{MON.map((m, i) => <span key={m} role="cell" aria-label={irr.has(i + 1) ? `${m} irrigated` : ''} className={`sp-cell ${irr.has(i + 1) ? 'irr on' : ''} ${i + 1 >= cw[0] && i + 1 <= cw[1] ? 'crit' : ''}`} />)}</div>
        {rows.map((sp, k) => (
          <div className="sp-srow" role="row" key={k} title={`${sp.common}. ${sp.stage}`}>
            <span className="sp-slab">{rowName(sp)}</span>
            {sp.months.length === 0
              ? <span className="sp-nopub" role="cell">Months not published</span>
              : MON.map((m, i) => <span key={m} role="cell" aria-label={sp.months.includes(i + 1) ? `${m}: ${rowName(sp)}` : ''} className={`sp-cell ${irr.has(i + 1) ? 'irr' : ''} ${i + 1 >= cw[0] && i + 1 <= cw[1] ? 'crit' : ''}`}>{sp.months.includes(i + 1) && <i className="sp-fish" style={{ background: FISH_COL }} />}</span>)}
          </div>
        ))}
      </div>
      <ul className="sp-key">
        <li><i className="sp-sw irr" /> Months the field is irrigated</li>
        <li><i className="sp-sw crit" /> Aug and Sep, the critical weeks</li>
      </ul>
      <p className="sp-note">Young Chinook and coho stay in the river all year. Months come from Salmon River sources where we found them.</p>
    </div>
  );
}

// ---------- water left for salmon ----------
function WaterLeft({ s }: { s: Salmon }) {
  const w = s.water_for_salmon;
  const low = w.reference_low_flow.value;
  const rows = w.scale_up.rows.filter((r) => r.licences.value === Math.max(...w.scale_up.rows.map((x) => x.licences.value)));
  return (
    <div className="sp-block" data-testid="salmon-water">
      <div className="sp-head"><h3>Water left for salmon</h3></div>
      <p className="sp-lede">How much of a low August flow ({f2(low)} m³/s) this field would take in Aug and Sep, by rotation.</p>
      <ul className="sp-bars">
        {w.items.map((it) => {
          const pct = it.share_of_low_aug_flow_pct.value;
          return (
            <li key={it.strategy_id} title={it.draw_aug_sep_m3.low != null ? `Between ${num(it.draw_aug_sep_m3.low)} and ${num(it.draw_aug_sep_m3.high ?? 0)} m³ over Aug and Sep` : undefined}>
              <div className="sp-bar-top"><span>{it.short_name}</span><b>{pct === 0 ? '0%' : `${pct.toFixed(2).replace(/0$/, '')}%`}</b></div>
              <div className="sp-track" aria-hidden="true"><i style={{ width: `${clamp(pct, 0, 1) * 100}%` }} /></div>
              <small>{it.irrigated_in_window ? `${it.draw_rate_l_s.value.toFixed(1)} L/s, ${num(it.draw_aug_sep_m3.value)} m³ over Aug and Sep` : 'No water taken in Aug and Sep'}</small>
            </li>
          );
        })}
      </ul>
      <p className="sp-scale"><span>0%</span><span>1% of a low August flow</span></p>
      <div className="sp-illus">
        <h4><span className="status example">Illustration</span> {w.scale_up.label.replace(/^Illustration:\s*/, '').replace(/^./, (c) => c.toUpperCase())}</h4>
        <div className="sp-table-wrap">
          <table className="sp-table">
            <thead><tr><th scope="col">Licences</th><th scope="col">Each waters</th><th scope="col">Draw</th><th scope="col">Of a low August flow</th></tr></thead>
            <tbody>
              {rows.map((r) => {
                const p = r.share_of_low_aug_flow_pct.value;
                return <tr key={r.assumed_ha_per_licence.value} className={p >= 100 ? 'over' : ''}><td>{num(r.licences.value)}</td><td>{r.assumed_ha_per_licence.value} ha</td><td>{num(r.draw_rate_l_s.value)} L/s</td><td><b>{Math.round(p)}%</b></td></tr>;
              })}
            </tbody>
          </table>
        </div>
        <p className="sp-note">{w.scale_up.note} Over 100% means more than a low August river carries.</p>
      </div>
      <cite className="sp-cite">CropLytics water-balance model, spread evenly over 61 days with 75% sprinkler efficiency (assumed). Licence counts: BC news release, 2026.</cite>
    </div>
  );
}

// ---------- early warning ----------
function EarlyWarning({ s }: { s: Salmon }) {
  const ew = s.early_warning;
  const [open, setOpen] = useState(false);
  const word = (p?: number) => (p == null ? 'n/a' : p <= 33 ? 'Dry' : p >= 67 ? 'Wet' : 'Middle');
  const table = [...ew.table].sort((a, b) => b.year - a.year);
  return (
    <div className="sp-block" data-testid="salmon-warning">
      <div className="sp-head"><h3>Can a dry spring warn us?</h3></div>
      <p className="sp-tag">{ew.label}</p>
      <div className="sp-table-wrap">
        <table className="sp-table sp-ew">
          <thead><tr><th scope="col">Spring sign</th><th scope="col">Low August after a dry one</th><th scope="col" title="0 = driest on record, 100 = wettest">How 2026 looked</th></tr></thead>
          <tbody>
            {ew.indicators.map((i) => (
              <tr key={i.indicator}>
                <td>{i.label}<small>{i.n_years} years</small></td>
                <td title={`Rank correlation ${i.spearman_r.value.toFixed(2)}`}><b>{i.driest_third_with_low_august.length} of {i.driest_third_years.length}</b><small>strength {i.spearman_r.value.toFixed(2)}</small></td>
                <td title="0 = driest on record, 100 = wettest"><b>{word(i.pct_rank_2026?.value)}</b><small>{i.pct_rank_2026 ? `${Math.round(i.pct_rank_2026.value)} of 100` : ''}</small></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {ew.note && <p className="sp-note">{ew.note}</p>}
      <button type="button" className="btn btn-text btn-sm sp-yby" aria-expanded={open} onClick={() => setOpen(!open)} data-testid="salmon-yby">{open ? 'Hide year by year' : 'Show year by year'}</button>
      {open && (
        <div className="sp-table-wrap sp-scroll">
          <table className="sp-table">
            <thead><tr><th scope="col">Year</th><th scope="col">August flow, m³/s</th><th scope="col">Snow in late Apr</th><th scope="col">Winter precip, mm</th></tr></thead>
            <tbody>{table.map((r) => <tr key={r.year} className={r.year === 2026 ? 'now' : ''}><td>{r.year}</td><td>{r.aug_mean_m3s != null ? f2(r.aug_mean_m3s) : '-'}</td><td>{r.snow_late_apr_frac != null ? `${Math.round(r.snow_late_apr_frac * 100)}%` : '-'}</td><td>{r.eccc_nov_mar_precip_mm != null ? Math.round(r.eccc_nov_mar_precip_mm) : '-'}</td></tr>)}</tbody>
          </table>
        </div>
      )}
      <cite className="sp-cite">Water Survey of Canada, NASA MODIS snow cover, NASA GPM IMERG rain, Environment and Climate Change Canada stations.</cite>
    </div>
  );
}

// ---------- the section ----------
export function SalmonPanel({ locId }: { locId: string }) {
  const [s, setS] = useState<Salmon | null>(null);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    let ok = true; setS(null);
    const ctl = new AbortController(), h = setTimeout(() => ctl.abort(), 30000);
    fetch(`${API_BASE}/locations/${locId}/salmon`, { signal: ctl.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((b) => { if (ok && b?.flow?.daily && b.summary) setS(b as Salmon); })
      .catch(() => { /* no salmon page for this field: render nothing */ })
      .finally(() => clearTimeout(h));
    return () => { ok = false; ctl.abort(); clearTimeout(h); };
  }, [locId]);
  if (!s) return null;
  const lead = [s.summary[0], s.summary[3], s.summary[4]].filter(Boolean);
  return (
    <section className="sp" data-testid="salmon">
      <h2 className="fp-h">Salmon and the field</h2>
      <div className="sp-summary">{lead.map((t) => <p key={t}>{t}</p>)}</div>
      <button className="more-detail" onClick={() => setOpen(!open)} aria-expanded={open} aria-controls="sp-more" data-testid="salmon-more">
        <span><b>{open ? 'Less detail' : 'More detail'}</b><small>{open ? 'Back to the short version' : 'Flow, water temperature, run timing'}</small></span><Icon name="chevdown" size={20} />
      </button>
      <div className={`sp-more ${open ? 'on' : ''}`} id="sp-more"><div className="sp-more-in">
        <FlowChart s={s} />
        <TempChart s={s} />
        <RunTiming s={s} />
        <WaterLeft s={s} />
        <EarlyWarning s={s} />
      </div></div>
      <div className="sp-respect" data-testid="salmon-respect">
        {s.respect.statements.map((t) => <p key={t}>{t}</p>)}
        <ul>{s.respect.links.map((l) => <li key={l.url}><a href={l.url} target="_blank" rel="noreferrer">{l.title}</a></li>)}</ul>
      </div>
    </section>
  );
}
