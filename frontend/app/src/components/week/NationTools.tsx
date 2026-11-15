import { ReadAloud } from '../help/ReadAloud';
import { motionOff } from '../a11y/prefs';
// "Nation tools" (field panel): land status and nearby Nations, drought rotation, groundwater, land and season, funding.
// Routes: GET /api/locations/{id}/nation and /nation/{drought_rotation,groundwater,land_season,funding}, report.pdf.
// Neutral and factual: Nations are named only as sourced facts, never as partners or endorsers. Cards load when opened.
import { useState } from 'react';
import type { Location } from '../../types';
import { API_BASE, sectionGap } from '../../api';
import { t, locale } from '../../i18n';
import Icon from '../Icons';
import { RouteProblem, SKEL, useRoute } from './useRoute';
import './nation.css';

interface Link { title?: string; url: string; verified?: boolean }
interface Summary {
  location_id: string; location: { jurisdiction: string; region: string };
  land_status: { value: string; detail?: string; area_name?: string | null; nation?: string | null; source?: Link };
  nearest_nations: { nation: string; nearest_area: string; area_kind: string; distance_km: number; inside: boolean }[];
  search_radius_km?: number;
  place_names: { name: string; english?: string; nation?: string; source_url: string; source_type?: string; approved_by_nation?: boolean }[];
  caveats?: string[];
}
interface Rot { id: string; name: string; is_baseline?: boolean; water_mm_season: number; share_after_cutoff_pct: number; irrigation_need_af_ac?: number; dry_year_rank?: number }
interface Drought {
  cutoff_date: string; cutoff_note?: string; rotations: Rot[];
  cutoff_scenarios: { cutoff_date: string; is_requested: boolean; rotations: { id: string; unmet_water_share_pct: number | null }[] }[];
  drought_history: { year: number; partial: boolean; imerg_precip_anom_pct: number | null; smap_rootzone_pctl: number | null; gracedadm_gw_pctl: number | null; power_et0_mm: number | null }[];
  history_basis?: string; caveats?: string[];
}
interface Groundwater {
  subbasin_title?: string; b118_subbasin_name?: string; sgma_priority?: string; gsas?: { name: string; url?: string }[]; gsa_names?: string[];
  sgma_status?: string; sgma_status_url?: string; gw_pctl_weekly: { week_start: string; gw_pctl: number }[]; gw_pctl_status?: { status: string; reason?: string | null };
  pumping_need_af_by_rotation: { id: string; name: string; pumping_need_af: number; irrigation_need_af_per_acre: number; acres: number }[]; pumping_note?: string;
  tribal_links: Link[]; caveat: string;
}
interface Land {
  ndvi_status?: { status: string; reason?: string | null };
  phenology?: { greenup_doy?: number | null; peak_doy?: number | null; senescence_doy?: number | null } | null; phenology_note?: string;
  snow?: { status: string; reason?: string | null; snow_off_doy?: number | null; scope?: string; years?: { year: number; snow_off_doy: number }[] };
  fire_detections_7d?: { status: string; count: number; within_km: number; reason?: string | null };
  fire_detections_365d?: { status: string; count: number; reason?: string | null };
  burn_scars?: { source: string; url: string }[]; regs_links?: Link[]; harvest_rights_note?: string;
}
interface Program {
  id: string; name: string; agency: string; eligible: string; typical_amount: string; status: string; deadline: string | null; status_note?: string;
  url: string; verified?: boolean; how_croplytics_helps?: string; matched_reason?: string;
}
interface Funding { jurisdiction: string; programs: Program[]; disclaimer?: string; as_of?: string }

const MON = Array.from({ length: 12 }, (_, i) => t(`week.mon${i}`));
const doy = (n: number) => { const d = new Date(Date.UTC(2023, 0, n)); return t('week.dateMD', { m: MON[d.getUTCMonth()], d: d.getUTCDate() }); };
const mmdd = (s: string) => { const [m, d] = s.split('-').map(Number); return t('week.dateMD', { m: MON[m - 1], d }); };
const mi = (km: number) => (km * 0.621).toFixed(km < 16 ? 1 : 0);
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const LAND: Record<string, string> = { reserve: t('week.landReserve'), trust: t('week.landTrust'), fee: t('week.landFee'), private: t('week.landPrivate'), unknown: t('week.landUnknown'), first_nations_reserve: t('week.landReserve'), tribal_land: t('week.landTribal') };
const rotShort = (n: string) => n.replace(/\s*\((current|actual)\)/, '');

/** Open the Nation tools (waiting for them to load), scroll them into view and pulse them softly (not under reduced motion). */
export function focusNationTools(tries = 0) {
  const sec = document.querySelector<HTMLElement>('[data-testid="nation-tools"]');
  const tg = sec?.querySelector<HTMLButtonElement>('[data-testid="nation-toggle"]');
  if ((!sec || !tg) && tries < 60) { setTimeout(() => focusNationTools(tries + 1), 200); return; }
  if (!sec) return;
  if (tg && tg.getAttribute('aria-expanded') !== 'true') tg.click();
  const calm = motionOff();
  sec.scrollIntoView({ behavior: calm ? 'auto' : 'smooth', block: 'start' });
  if (!calm) { sec.classList.remove('nt-pulse'); void sec.offsetWidth; sec.classList.add('nt-pulse'); setTimeout(() => sec.classList.remove('nt-pulse'), 1300); }
}

/** Step 2, under the answer card: the nearest reserve at a glance, one tap to the Nation tools. */
export function NationChip({ loc, openDetail }: { loc: Location; openDetail: () => void }) {
  const f = loc.first_nations;
  if (!f || loc.mine) return null;
  const name = f.nearest_reserve.toLowerCase().replace(/(^|[\s(])(\p{L})/gu, (_m, a: string, b: string) => a + b.toUpperCase());
  return (
    <button className="nt-chip" data-testid="nation-chip" onClick={() => { openDetail(); setTimeout(() => focusNationTools(), 150); }}>
      <i />{f.field_on_reserve ? t('week.landReserve') : t('week.nearestReserve', { name, km: f.nearest_km })}<b>{t('week.nationTools')}</b>
    </button>
  );
}

/** Top of the field panel: shown only when the place is on reserve or trust land. */
export function ReservePill({ loc }: { loc: Location }) {
  const st = useRoute<Summary>(loc.spot && loc.spot.state !== 'ready' ? null : `/locations/${loc.id}/nation`, 40000);
  if (st.kind !== 'ok') return null;
  const s = st.data;
  if (!['reserve', 'trust', 'first_nations_reserve', 'tribal_land'].includes(s.land_status.value)) return null;
  const nation = s.land_status.nation ?? s.nearest_nations.find((n) => n.inside)?.nation ?? s.nearest_nations[0]?.nation;
  return <p className="res-pill" data-testid="reserve-pill" role="status"><i />{t('week.landReserve')}{nation ? `: ${nation}` : ''}</p>;
}

export function NationTools({ loc, defaultOpen = false }: { loc: Location; defaultOpen?: boolean }) {
  const sp = loc.spot;
  const [open, setOpen] = useState(defaultOpen);
  const st = useRoute<Summary>(sp && sp.state !== 'ready' ? null : `/locations/${loc.id}/nation`, 40000);
  if (st.kind === 'missing') return null;
  const s = st.kind === 'ok' ? st.data : null;
  return (
    <section className="nt" data-testid="nation-tools" aria-label={t('week.nationTools')}>
      <h2 className="fp-h">{t('week.nationTools')}</h2>
      <p className="nt-lede">{t('week.lede')}</p>
      {st.kind === 'loading' && SKEL(2)}
      <RouteProblem st={st} what={t('week.nationTools')} reload={st.reload} />
      {s && <Header s={s} />}
      {s && (
        <>
          <button className={`more-detail nt-toggle ${open ? 'on' : ''}`} onClick={() => setOpen(!open)} aria-expanded={open} data-testid="nation-toggle">
            <span><b>{open ? t('week.hideTools') : t('week.openTools')}</b><small>{t('week.toolsSub')}</small></span><Icon name="chevdown" size={20} />
          </button>
          <div className={`nt-more ${open ? 'on' : ''}`}><div className="nt-more-in">{open && <Tools loc={loc} s={s} />}</div></div>
        </>
      )}
    </section>
  );
}

function Header({ s }: { s: Summary }) {
  const near = s.nearest_nations.slice(0, 3);
  const names = s.place_names;
  return (
    <div className="nt-head">
      <p className="nt-status"><b>{LAND[s.land_status.value] ?? cap(s.land_status.value.replace(/_/g, ' '))}</b>{s.land_status.area_name ? ` (${s.land_status.area_name})` : ''}
        {s.land_status.source?.url && <> <a href={s.land_status.source.url} target="_blank" rel="noreferrer">{t('week.source')}</a></>}</p>
      {near.length > 0 && (
        <ul className="nt-near" aria-label={t('week.nearAria')}>
          {near.map((n) => <li key={n.nation + n.nearest_area}><span><b>{n.nation}</b><small>{n.nearest_area === n.nearest_area.toUpperCase() ? n.nearest_area.toLowerCase().replace(/(^|[\s(])(\p{L})/gu, (_m, a: string, b: string) => a + b.toUpperCase()) : n.nearest_area}</small></span><em>{n.inside ? t('week.inside') : t('week.miAway', { n: mi(n.distance_km) })}</em></li>)}
        </ul>
      )}
      <ReadAloud text={`${LAND[s.land_status.value] ?? cap(s.land_status.value.replace(/_/g, ' '))}${s.land_status.area_name ? `, ${s.land_status.area_name}` : ''}.${near.length ? t('merge.nt.nearest', { list: near.map((n) => `${n.nation}, ${n.inside ? t('merge.nt.inside') : t('merge.nt.away', { n: mi(n.distance_km) })}`).join('; ') }) : ''}`} />
      <p className="nt-fine">{t('week.nearNote')}</p>
      {names.length > 0 && (
        <div className="nt-names">
          <h3>{t('week.placeNames')}</h3>
          <ul>
            {names.map((p) => (
              <li key={p.name}><b>{p.name}</b>{p.english ? ` (${p.english})` : ''}{p.nation ? t('week.writtenBy', { nation: p.nation }) : ''}.{' '}
                <a href={p.source_url} target="_blank" rel="noreferrer">{t('week.source')}</a>
                {p.approved_by_nation === false && <span className="nt-flag"> {t('week.notConfirmed')}</span>}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function Tools({ loc, s }: { loc: Location; s: Summary }) {
  const base = `/locations/${loc.id}/nation`;
  const [cutoff, setCutoff] = useState('08-15');
  const bc = loc.region === 'bc';
  const gap = bc ? null : sectionGap(loc);
  return (
    <div className="nt-cards">
      <Drought base={base} cutoff={cutoff} setCutoff={setCutoff} />
      {bc ? <BcWater id={loc.id} /> : loc.region === 'other' ? <Card title="Groundwater" id="groundwater"><p className="gap-line">{t('nt.gwCaOnly')}</p></Card> : gap ? <Card title="Groundwater" id="groundwater"><p className="gap-line">Not available here. {gap}</p></Card> : <Groundwater base={base} />}
      <LandSeason base={base} />
      {!gap && <FundingCard base={base} id={loc.id} jur={bc || s.location?.jurisdiction === 'BC' ? 'BC' : 'CA'} cutoff={cutoff} />}
    </div>
  );
}

const Card = ({ title, id, children }: { title: string; id: string; children: React.ReactNode }) => (
  <div className="nt-card" data-testid={`nt-${id}`}><h3>{title}</h3>{children}</div>
);
function Load<T>({ st, what, children }: { st: ReturnType<typeof useRoute<T>>; what: string; children: (d: T) => React.ReactNode }) {
  if (st.kind === 'loading') return SKEL(3);
  if (st.kind === 'missing') return <p className="gap-line">{t('week.notAvail')}</p>;
  if (st.kind !== 'ok') return RouteProblem({ st, what, reload: st.reload });
  return <>{children(st.data)}</>;
}

function Drought({ base, cutoff, setCutoff }: { base: string; cutoff: string; setCutoff: (c: string) => void }) {
  const st = useRoute<Drought>(`${base}/drought_rotation?cutoff=${cutoff}`);
  const year = new Date().getFullYear();
  return (
    <Card title={t('week.droughtTitle')} id="drought">
      <label className="nt-field">{t('week.waterStopsOn')}
        <input type="date" value={`${year}-${cutoff}`} min={`${year}-05-01`} max={`${year}-10-31`}
          onChange={(e) => { const v = e.target.value; if (/^\d{4}-\d{2}-\d{2}$/.test(v)) setCutoff(v.slice(5)); }} data-testid="nation-cutoff" /></label>
      <Load st={st} what={t('week.theDrought')}>{(d) => {
        const peak = Math.max(1, ...d.rotations.map((r) => r.share_after_cutoff_pct));
        const base0 = d.rotations.find((r) => r.is_baseline) ?? d.rotations[0];
        return (
          <div key={d.cutoff_date} className="nt-fade">
            <p className="nt-q">{t('week.shareAfter', { date: mmdd(d.cutoff_date) })}</p>
            <ul className="nt-bars">
              {d.rotations.map((r, i) => (
                <li key={r.id}><span className="nt-bl">{rotShort(r.name)}{r.is_baseline ? ` ${t('week.current')}` : ''}</span>
                  <i className="nt-track"><em style={{ '--p': r.share_after_cutoff_pct / peak, '--i': i } as React.CSSProperties} /></i>
                  <b>{Math.round(r.share_after_cutoff_pct)}%</b>
                  {r.dry_year_rank != null && <small>{t('week.dryRank', { r: r.dry_year_rank, n: d.rotations.length })}</small>}</li>
              ))}
            </ul>
            <p className="nt-fine">{t('week.shareNote')}</p>
            <h4>{t('week.otherCutoffs')}</h4>
            <table className="nt-table"><thead><tr><th>{t('week.thStops')}</th><th>{rotShort(base0.name)}</th><th>{t('week.thLowest')}</th></tr></thead>
              <tbody>{d.cutoff_scenarios.map((sc) => {
                const vals = sc.rotations.filter((r) => r.unmet_water_share_pct != null);
                const mine = vals.find((r) => r.id === base0.id)?.unmet_water_share_pct;
                const low = vals.length ? vals.reduce((a, b) => (b.unmet_water_share_pct! < a.unmet_water_share_pct! ? b : a)) : null;
                return <tr key={sc.cutoff_date} className={sc.is_requested ? 'on' : ''}><td>{mmdd(sc.cutoff_date)}</td><td>{mine != null ? t('week.unmet', { n: Math.round(mine) }) : '–'}</td><td>{low ? `${Math.round(low.unmet_water_share_pct!)}%` : '–'}</td></tr>;
              })}</tbody></table>
            <details className="nt-det"><summary>{t('week.histSummary')}</summary>
              <div className="nt-scroll"><table className="nt-table"><thead><tr><th>{t('week.thYear')}</th><th>{t('week.thRain')}</th><th>{t('week.thGw')}</th><th>{t('week.thSoil')}</th></tr></thead>
                <tbody>{d.drought_history.map((h) => (
                  <tr key={h.year}><td>{h.year}{h.partial ? '*' : ''}</td><td>{h.imerg_precip_anom_pct != null ? `${h.imerg_precip_anom_pct > 0 ? '+' : ''}${Math.round(h.imerg_precip_anom_pct)}%` : '–'}</td>
                    <td>{h.gracedadm_gw_pctl != null ? t('week.pct', { n: Math.round(h.gracedadm_gw_pctl) }) : '–'}</td><td>{h.smap_rootzone_pctl != null ? t('week.pct', { n: Math.round(h.smap_rootzone_pctl) }) : t('week.notYet')}</td></tr>))}</tbody></table></div>
              <p className="nt-fine">{d.history_basis} {t('week.histNote')}</p>
            </details>
            {d.caveats?.[0] && <p className="nt-fine">{d.caveats[0]}</p>}
          </div>
        );
      }}</Load>
    </Card>
  );
}

function Spark({ pts }: { pts: { week_start: string; gw_pctl: number }[] }) {
  const w = 300, h = 56, n = pts.length;
  const d = pts.map((p, i) => `${i ? 'L' : 'M'}${((i / Math.max(1, n - 1)) * w).toFixed(1)},${(h - (p.gw_pctl / 100) * h).toFixed(1)}`).join('');
  const last = pts[n - 1];
  return (
    <figure className="nt-spark">
      <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" role="img" aria-label={t('week.sparkAria', { a: pts[0].week_start.slice(0, 4), b: last.week_start.slice(0, 4), n: Math.round(last.gw_pctl) })}>
        <line x1="0" x2={w} y1={h / 2} y2={h / 2} className="mid" /><path d={d} pathLength={1} />
      </svg>
      <figcaption><span>{pts[0].week_start.slice(0, 4)}</span><span>{t('week.sparkLatest', { n: Math.round(last.gw_pctl) })}</span></figcaption>
    </figure>
  );
}

function Groundwater({ base }: { base: string }) {
  const st = useRoute<Groundwater>(`${base}/groundwater`);
  return (
    <Card title={t('week.gwTitle')} id="groundwater">
      <Load st={st} what={t('week.gwTitle')}>{(g) => (
        <div className="nt-fade">
          <p className="nt-q"><b>{g.subbasin_title ?? g.b118_subbasin_name}</b>{g.sgma_priority ? t('week.priorityBasin', { p: g.sgma_priority.toLowerCase() }) : ''}</p>
          {(g.gsas?.length ?? 0) > 0 && <p className="nt-row"><span>{t('week.gwAgency')}</span>{g.gsas!.map((x, i) => <span key={x.name}>{i ? '; ' : ''}{x.url ? <a href={/^https?:/.test(x.url) ? x.url : `https://${x.url}`} target="_blank" rel="noreferrer">{x.name}</a> : x.name}</span>)}</p>}
          {g.sgma_status && <p className="nt-row"><span>{t('week.sgmaStatus')}</span><span>{g.sgma_status}{g.sgma_status_url && <> <a href={g.sgma_status_url} target="_blank" rel="noreferrer">{t('week.source')}</a></>}</span></p>}
          {g.gw_pctl_weekly.length > 1 ? <Spark pts={g.gw_pctl_weekly} /> : g.gw_pctl_status?.reason ? <p className="gap-line">{cap(g.gw_pctl_status.reason)}.</p> : null}
          <h4>{t('week.pumpingH')}</h4>
          <ul className="nt-pump">{g.pumping_need_af_by_rotation.map((r) => <li key={r.id}><span>{rotShort(r.name)}</span><b>{Math.round(r.pumping_need_af).toLocaleString(locale)} {t('week.acreFt')}</b></li>)}</ul>
          {g.pumping_note && <p className="nt-fine">{g.pumping_note}</p>}
          {g.tribal_links.length > 0 && <><h4>{t('week.tribalSgma')}</h4><ul className="nt-links">{g.tribal_links.map((l) => <li key={l.url}><a href={l.url} target="_blank" rel="noreferrer">{l.title}</a></li>)}</ul></>}
          <p className="nt-caveat">{g.caveat}</p>
        </div>
      )}</Load>
    </Card>
  );
}

function BcWater({ id }: { id: string }) {
  const st = useRoute<{ summary: string[] }>(`/locations/${id}/salmon`);
  const jump = () => document.querySelector('.sp')?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
  return (
    <Card title={t('week.bcTitle')} id="groundwater">
      <p className="nt-fine">{t('week.bcNote')}</p>
      {st.kind === 'ok' && st.data.summary.slice(0, 2).map((x) => <p key={x} className="nt-q">{x}</p>)}
      <button className="btn btn-text btn-sm" onClick={jump}>{t('week.goSalmon')}</button>
    </Card>
  );
}

function LandSeason({ base }: { base: string }) {
  const st = useRoute<Land>(`${base}/land_season`);
  return (
    <Card title={t('week.landTitle')} id="land">
      <Load st={st} what={t('week.landTitle')}>{(l) => {
        const ph = l.phenology, has = ph && ph.greenup_doy != null;
        const f7 = l.fire_detections_7d, f365 = l.fire_detections_365d;
        return (
          <div className="nt-fade">
            {has ? <>
              <p className="nt-row"><span>{t('week.greenUp')}</span><b>{doy(ph!.greenup_doy!)}</b></p>
              <p className="nt-row"><span>{t('week.peakGreen')}</span><b>{ph!.peak_doy != null ? doy(ph!.peak_doy) : '–'}</b></p>
              <p className="nt-row"><span>{t('week.greenFades')}</span><b>{ph!.senescence_doy != null ? doy(ph!.senescence_doy) : '–'}</b></p>
              <p className="nt-fine">{l.phenology_note}</p></> :
              <p className="gap-line">{t('week.greenDates')} {l.ndvi_status?.reason ? cap(l.ndvi_status.reason) + '.' : t('week.notComputed')}</p>}
            {l.snow?.status === 'real' && l.snow.snow_off_doy != null && <><p className="nt-row"><span>{t('week.snowGone')}</span><b>{doy(l.snow.snow_off_doy)}</b></p><p className="nt-fine">{t('week.snowNote', { n: l.snow.years?.length ?? 1 })}</p></>}
            {f7 && (f7.status === 'real' ? <p className="nt-row"><span>{t('week.fire7', { mi: mi(f7.within_km) })}</span><b>{f7.count}</b></p> : <p className="gap-line">{t('week.fire7b')} {f7.reason ?? t('week.notAvailable')}.</p>)}
            {f365 && f365.status !== 'real' && <p className="gap-line">{t('week.fire365')} {f365.reason ? cap(f365.reason.split('. ')[0]).replace(/\.$/, '') + '.' : t('week.notAvailableDot')}</p>}
            <ul className="nt-links">
              {l.burn_scars?.map((b) => <li key={b.url}><a href={b.url} target="_blank" rel="noreferrer">{t('week.burnScars')} {b.source}</a></li>)}
              {l.regs_links?.map((b) => <li key={b.url}><a href={b.url} target="_blank" rel="noreferrer">{t('week.regs')} {b.title}</a></li>)}
            </ul>
            {l.harvest_rights_note && <p className="nt-caveat">{l.harvest_rights_note}</p>}
          </div>
        );
      }}</Load>
    </Card>
  );
}

const STATUS: Record<string, string> = { open: t('week.stOpen'), rolling: t('week.stRolling'), closed: t('week.stClosed'), unknown: t('week.stUnknown') };
function FundingCard({ base, id, jur, cutoff }: { base: string; id: string; jur: string; cutoff: string }) {
  const st = useRoute<Funding>(`${base}/funding?jurisdiction=${jur}`);
  return (
    <Card title={t('week.fundingTitle', { where: jur === 'BC' ? t('week.whereBC') : t('week.whereCA') })} id="funding">
      <Load st={st} what={t('week.fundingWhat')}>{(f) => (
        <div className="nt-fade">
          <ul className="nt-prog">
            {f.programs.map((p) => (
              <li key={p.id}>
                <div className="nt-ph"><a href={p.url} target="_blank" rel="noreferrer"><b>{p.name}</b></a><span className={`nt-st ${p.status}`}>{STATUS[p.status] ?? p.status}</span></div>
                <p className="nt-fine">{p.agency}{p.deadline ? ` · ${p.deadline}` : ''}</p>
                <p className="nt-row"><span>{t('week.typicalAmount')}</span><span>{p.typical_amount}</span></p>
                <p className="nt-row"><span>{t('week.whoApply')}</span><span>{p.eligible}</span></p>
                {p.how_croplytics_helps && <p className="nt-row"><span>{t('week.howHelps')}</span><span>{p.how_croplytics_helps}</span></p>}
                {p.verified === false && <p className="nt-fine">{t('week.notVerified')}</p>}
                <a className="btn btn-outline btn-sm" href={`${API_BASE}/locations/${id}/nation/report.pdf?program=${encodeURIComponent(p.id)}&cutoff=${cutoff}`} target="_blank" rel="noreferrer">{t('week.downloadReport')}</a>
              </li>
            ))}
          </ul>
          <p className="nt-fine">{f.disclaimer} {t('week.fundDisclaimer')}</p>
        </div>
      )}</Load>
    </Card>
  );
}
