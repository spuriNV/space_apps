// "Nation tools" (field panel): land status and nearby Nations, drought rotation, groundwater, land and season, funding.
// Routes: GET /api/locations/{id}/nation and /nation/{drought_rotation,groundwater,land_season,funding}, report.pdf.
// Neutral and factual: Nations are named only as sourced facts, never as partners or endorsers. Cards load when opened.
import { useState } from 'react';
import type { Location } from '../../types';
import { API_BASE } from '../../api';
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

const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const doy = (n: number) => { const d = new Date(Date.UTC(2023, 0, n)); return `${MON[d.getUTCMonth()]} ${d.getUTCDate()}`; };
const mmdd = (s: string) => { const [m, d] = s.split('-').map(Number); return `${MON[m - 1]} ${d}`; };
const mi = (km: number) => (km * 0.621).toFixed(km < 16 ? 1 : 0);
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const LAND: Record<string, string> = { reserve: 'On reserve land', trust: 'On trust land', fee: 'On fee land within a reservation', private: 'Not on reserve or trust land', unknown: 'Land status not known', first_nations_reserve: 'On reserve land', tribal_land: 'On tribal land' };
const rotShort = (n: string) => n.replace(' (current)', '');

export function NationTools({ loc }: { loc: Location }) {
  const sp = loc.spot;
  const [open, setOpen] = useState(false);
  const st = useRoute<Summary>(sp && sp.state !== 'ready' ? null : `/locations/${loc.id}/nation`, 40000);
  if (st.kind === 'missing') return null;
  const s = st.kind === 'ok' ? st.data : null;
  return (
    <section className="nt" data-testid="nation-tools" aria-label="Nation tools">
      <h2 className="fp-h">Nation tools</h2>
      <p className="nt-lede">Water, land and funding facts for Nations and tribal farm and lands staff. Public data only.</p>
      {st.kind === 'loading' && SKEL(2)}
      <RouteProblem st={st} what="Nation tools" reload={st.reload} />
      {s && <Header s={s} />}
      {s && (
        <>
          <button className={`more-detail nt-toggle ${open ? 'on' : ''}`} onClick={() => setOpen(!open)} aria-expanded={open} data-testid="nation-toggle">
            <span><b>{open ? 'Hide the tools' : 'Open the tools'}</b><small>Drought rotation, groundwater, land and season, funding</small></span><Icon name="chevdown" size={20} />
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
        {s.land_status.source?.url && <> <a href={s.land_status.source.url} target="_blank" rel="noreferrer">Source</a></>}</p>
      {near.length > 0 && (
        <ul className="nt-near" aria-label="Nearest Nations by distance">
          {near.map((n) => <li key={n.nation + n.nearest_area}><span><b>{n.nation}</b><small>{n.nearest_area === n.nearest_area.toUpperCase() ? n.nearest_area.toLowerCase().replace(/(^|[\s(])(\p{L})/gu, (_m, a: string, b: string) => a + b.toUpperCase()) : n.nearest_area}</small></span><em>{n.inside ? 'Inside' : `${mi(n.distance_km)} mi away`}</em></li>)}
        </ul>
      )}
      <p className="nt-fine">Listed by distance only. Reserve and trust boundaries are legal lines, not traditional territory.</p>
      {names.length > 0 && (
        <div className="nt-names">
          <h3>Place names</h3>
          <ul>
            {names.map((p) => (
              <li key={p.name}><b>{p.name}</b>{p.english ? ` (${p.english})` : ''}{p.nation ? `, as written by ${p.nation}` : ''}.{' '}
                <a href={p.source_url} target="_blank" rel="noreferrer">Source</a>
                {p.approved_by_nation === false && <span className="nt-flag"> Not confirmed by the Nation.</span>}</li>
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
  return (
    <div className="nt-cards">
      <Drought base={base} cutoff={cutoff} setCutoff={setCutoff} />
      {bc ? <BcWater id={loc.id} /> : <Groundwater base={base} />}
      <LandSeason base={base} />
      <FundingCard base={base} id={loc.id} jur={bc || s.location?.jurisdiction === 'BC' ? 'BC' : 'CA'} cutoff={cutoff} />
    </div>
  );
}

const Card = ({ title, id, children }: { title: string; id: string; children: React.ReactNode }) => (
  <div className="nt-card" data-testid={`nt-${id}`}><h3>{title}</h3>{children}</div>
);
function Load<T>({ st, what, children }: { st: ReturnType<typeof useRoute<T>>; what: string; children: (d: T) => React.ReactNode }) {
  if (st.kind === 'loading') return SKEL(3);
  if (st.kind === 'missing') return <p className="gap-line">Not available for this place.</p>;
  if (st.kind !== 'ok') return RouteProblem({ st, what, reload: st.reload });
  return <>{children(st.data)}</>;
}

function Drought({ base, cutoff, setCutoff }: { base: string; cutoff: string; setCutoff: (c: string) => void }) {
  const st = useRoute<Drought>(`${base}/drought_rotation?cutoff=${cutoff}`);
  const year = new Date().getFullYear();
  return (
    <Card title="Drought rotation" id="drought">
      <label className="nt-field">If irrigation water stops on
        <input type="date" value={`${year}-${cutoff}`} min={`${year}-05-01`} max={`${year}-10-31`}
          onChange={(e) => { const v = e.target.value; if (/^\d{4}-\d{2}-\d{2}$/.test(v)) setCutoff(v.slice(5)); }} data-testid="nation-cutoff" /></label>
      <Load st={st} what="The drought rotation">{(d) => {
        const peak = Math.max(1, ...d.rotations.map((r) => r.share_after_cutoff_pct));
        const base0 = d.rotations.find((r) => r.is_baseline) ?? d.rotations[0];
        return (
          <div key={d.cutoff_date} className="nt-fade">
            <p className="nt-q">Share of each rotation's crop water use that falls after {mmdd(d.cutoff_date)}</p>
            <ul className="nt-bars">
              {d.rotations.map((r, i) => (
                <li key={r.id}><span className="nt-bl">{rotShort(r.name)}{r.is_baseline ? ' (current)' : ''}</span>
                  <i className="nt-track"><em style={{ '--p': r.share_after_cutoff_pct / peak, '--i': i } as React.CSSProperties} /></i>
                  <b>{Math.round(r.share_after_cutoff_pct)}%</b>
                  {r.dry_year_rank != null && <small>Dry-year rank {r.dry_year_rank} of {d.rotations.length}</small>}</li>
              ))}
            </ul>
            <p className="nt-fine">A lower share means less of the crop's water is needed once the water stops. Rank 1 is the rotation that does best in a dry year. Estimates from the rotation model, not a guarantee.</p>
            <h4>Other cutoff dates</h4>
            <table className="nt-table"><thead><tr><th>Water stops</th><th>{rotShort(base0.name)}</th><th>Lowest</th></tr></thead>
              <tbody>{d.cutoff_scenarios.map((sc) => {
                const vals = sc.rotations.filter((r) => r.unmet_water_share_pct != null);
                const mine = vals.find((r) => r.id === base0.id)?.unmet_water_share_pct;
                const low = vals.length ? vals.reduce((a, b) => (b.unmet_water_share_pct! < a.unmet_water_share_pct! ? b : a)) : null;
                return <tr key={sc.cutoff_date} className={sc.is_requested ? 'on' : ''}><td>{mmdd(sc.cutoff_date)}</td><td>{mine != null ? `${Math.round(mine)}% unmet` : '–'}</td><td>{low ? `${Math.round(low.unmet_water_share_pct!)}%` : '–'}</td></tr>;
              })}</tbody></table>
            <details className="nt-det"><summary>Drought history, by water year</summary>
              <div className="nt-scroll"><table className="nt-table"><thead><tr><th>Year</th><th>Rain vs usual</th><th>Groundwater</th><th>Soil</th></tr></thead>
                <tbody>{d.drought_history.map((h) => (
                  <tr key={h.year}><td>{h.year}{h.partial ? '*' : ''}</td><td>{h.imerg_precip_anom_pct != null ? `${h.imerg_precip_anom_pct > 0 ? '+' : ''}${Math.round(h.imerg_precip_anom_pct)}%` : '–'}</td>
                    <td>{h.gracedadm_gw_pctl != null ? `${Math.round(h.gracedadm_gw_pctl)}th pct` : '–'}</td><td>{h.smap_rootzone_pctl != null ? `${Math.round(h.smap_rootzone_pctl)}th pct` : 'not yet'}</td></tr>))}</tbody></table></div>
              <p className="nt-fine">{d.history_basis} * = partial year. NASA GPM IMERG rain, NASA GRACE-DA groundwater.</p>
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
      <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" role="img" aria-label={`Groundwater percentile by week, ${pts[0].week_start.slice(0, 4)} to ${last.week_start.slice(0, 4)}. Latest ${Math.round(last.gw_pctl)}.`}>
        <line x1="0" x2={w} y1={h / 2} y2={h / 2} className="mid" /><path d={d} pathLength={1} />
      </svg>
      <figcaption><span>{pts[0].week_start.slice(0, 4)}</span><span>Latest: {Math.round(last.gw_pctl)}th percentile (50 is usual)</span></figcaption>
    </figure>
  );
}

function Groundwater({ base }: { base: string }) {
  const st = useRoute<Groundwater>(`${base}/groundwater`);
  return (
    <Card title="Groundwater" id="groundwater">
      <Load st={st} what="Groundwater">{(g) => (
        <div className="nt-fade">
          <p className="nt-q"><b>{g.subbasin_title ?? g.b118_subbasin_name}</b>{g.sgma_priority ? `, ${g.sgma_priority.toLowerCase()} priority basin` : ''}</p>
          {(g.gsas?.length ?? 0) > 0 && <p className="nt-row"><span>Groundwater agency</span>{g.gsas!.map((x, i) => <span key={x.name}>{i ? '; ' : ''}{x.url ? <a href={/^https?:/.test(x.url) ? x.url : `https://${x.url}`} target="_blank" rel="noreferrer">{x.name}</a> : x.name}</span>)}</p>}
          {g.sgma_status && <p className="nt-row"><span>SGMA status</span><span>{g.sgma_status}{g.sgma_status_url && <> <a href={g.sgma_status_url} target="_blank" rel="noreferrer">Source</a></>}</span></p>}
          {g.gw_pctl_weekly.length > 1 ? <Spark pts={g.gw_pctl_weekly} /> : g.gw_pctl_status?.reason ? <p className="gap-line">{cap(g.gw_pctl_status.reason)}.</p> : null}
          <h4>Pumping need by rotation</h4>
          <ul className="nt-pump">{g.pumping_need_af_by_rotation.map((r) => <li key={r.id}><span>{rotShort(r.name)}</span><b>{Math.round(r.pumping_need_af).toLocaleString()} acre-ft</b></li>)}</ul>
          {g.pumping_note && <p className="nt-fine">{g.pumping_note}</p>}
          {g.tribal_links.length > 0 && <><h4>Tribal engagement under SGMA</h4><ul className="nt-links">{g.tribal_links.map((l) => <li key={l.url}><a href={l.url} target="_blank" rel="noreferrer">{l.title}</a></li>)}</ul></>}
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
    <Card title="Water and salmon" id="groundwater">
      <p className="nt-fine">The groundwater tool covers California only. For this valley, the river and fish summary is below.</p>
      {st.kind === 'ok' && st.data.summary.slice(0, 2).map((t) => <p key={t} className="nt-q">{t}</p>)}
      <button className="btn btn-text btn-sm" onClick={jump}>Go to Salmon and the field</button>
    </Card>
  );
}

function LandSeason({ base }: { base: string }) {
  const st = useRoute<Land>(`${base}/land_season`);
  return (
    <Card title="Land and season" id="land">
      <Load st={st} what="Land and season">{(l) => {
        const ph = l.phenology, has = ph && ph.greenup_doy != null;
        const f7 = l.fire_detections_7d, f365 = l.fire_detections_365d;
        return (
          <div className="nt-fade">
            {has ? <>
              <p className="nt-row"><span>Green-up</span><b>{doy(ph!.greenup_doy!)}</b></p>
              <p className="nt-row"><span>Peak green</span><b>{ph!.peak_doy != null ? doy(ph!.peak_doy) : '–'}</b></p>
              <p className="nt-row"><span>Green fades</span><b>{ph!.senescence_doy != null ? doy(ph!.senescence_doy) : '–'}</b></p>
              <p className="nt-fine">{l.phenology_note}</p></> :
              <p className="gap-line">Green-up dates: {l.ndvi_status?.reason ? cap(l.ndvi_status.reason) + '.' : 'not computed for this place.'}</p>}
            {l.snow?.status === 'real' && l.snow.snow_off_doy != null && <><p className="nt-row"><span>Snow gone from the watershed</span><b>{doy(l.snow.snow_off_doy)}</b></p><p className="nt-fine">NASA MODIS, whole watershed, not the field. Latest year of {l.snow.years?.length ?? 1}.</p></>}
            {f7 && (f7.status === 'real' ? <p className="nt-row"><span>Fire detections, last 7 days (within {mi(f7.within_km)} mi)</span><b>{f7.count}</b></p> : <p className="gap-line">Fire detections, last 7 days: {f7.reason ?? 'not available'}.</p>)}
            {f365 && f365.status !== 'real' && <p className="gap-line">Fire detections, last year: {f365.reason ? cap(f365.reason.split('. ')[0]).replace(/\.$/, '') + '.' : 'not available.'}</p>}
            <ul className="nt-links">
              {l.burn_scars?.map((b) => <li key={b.url}><a href={b.url} target="_blank" rel="noreferrer">Burn scars: {b.source}</a></li>)}
              {l.regs_links?.map((b) => <li key={b.url}><a href={b.url} target="_blank" rel="noreferrer">Regulations: {b.title}</a></li>)}
            </ul>
            {l.harvest_rights_note && <p className="nt-caveat">{l.harvest_rights_note}</p>}
          </div>
        );
      }}</Load>
    </Card>
  );
}

const STATUS: Record<string, string> = { open: 'Open', rolling: 'Rolling', closed: 'Closed', unknown: 'Check dates' };
function FundingCard({ base, id, jur, cutoff }: { base: string; id: string; jur: string; cutoff: string }) {
  const st = useRoute<Funding>(`${base}/funding?jurisdiction=${jur}`);
  return (
    <Card title={`Funding (${jur === 'BC' ? 'British Columbia and Canada' : 'California and US'})`} id="funding">
      <Load st={st} what="Funding">{(f) => (
        <div className="nt-fade">
          <ul className="nt-prog">
            {f.programs.map((p) => (
              <li key={p.id}>
                <div className="nt-ph"><a href={p.url} target="_blank" rel="noreferrer"><b>{p.name}</b></a><span className={`nt-st ${p.status}`}>{STATUS[p.status] ?? p.status}</span></div>
                <p className="nt-fine">{p.agency}{p.deadline ? ` · ${p.deadline}` : ''}</p>
                <p className="nt-row"><span>Typical amount</span><span>{p.typical_amount}</span></p>
                <p className="nt-row"><span>Who can apply</span><span>{p.eligible}</span></p>
                {p.how_croplytics_helps && <p className="nt-row"><span>How CropLytics helps</span><span>{p.how_croplytics_helps}</span></p>}
                {p.verified === false && <p className="nt-fine">Details not yet confirmed on the program's own page.</p>}
                <a className="btn btn-outline btn-sm" href={`${API_BASE}/locations/${id}/nation/report.pdf?program=${encodeURIComponent(p.id)}&cutoff=${cutoff}`} target="_blank" rel="noreferrer">Download report</a>
              </li>
            ))}
          </ul>
          <p className="nt-fine">{f.disclaimer} Listing a program does not mean any Nation or agency endorses CropLytics.</p>
        </div>
      )}</Load>
    </Card>
  );
}
