import type { BCInfo, Calendar, CoverClass, Dataset, Location, NewsItem, Regional, RotationStrategy } from '../types';
import { CLASS_COLOR, CLASS_LABEL, GRACE_RAMP, SMAP_RAMP, YEARS, dateToT, fieldState, fmtDate, haToAc, ordinal, ramp, tLabel } from '../lib';
import Icon from './Icons';

const CDL_COLOR = (c: string) => (c.startsWith('Rice') ? '#4aa3ff' : c.startsWith('Fallow') ? '#a8703f' : c.startsWith('Alfalfa') ? '#3fbf6a' : '#e3c14f');

// ---------- Earth-style knowledge card ----------
export function KnowledgeCard(p: { loc: Location; cal: Calendar | null; regional: Regional | null; t: number; detector: 'rule' | 'ml'; news: NewsItem[]; setT: (t: number) => void; onDrill: () => void; onYear: () => void; onCompare: () => void; onStory: () => void; onClose: () => void }) {
  const { loc } = p;
  const fs = p.cal ? fieldState(p.cal, p.t, p.detector) : null;
  const smap = p.regional?.smap_rootzone_pct.values[p.t] ?? null;
  const grace = p.regional?.grace_gw_pct.values[p.t] ?? null;
  return (
    <section className="panel glass kcard" data-testid="kcard">
      <header className={`kc-hero ${loc.id}`}>
        <button className="icon-btn kc-close" onClick={p.onClose} title="Close"><Icon name="close" size={18} /></button>
        <span className="kc-eyebrow">{loc.valley} · California</span>
        <h1>{loc.short_name}</h1>
        <p>{loc.headline}</p>
        <div className="kc-badges">
          <span className="chip good"><Icon name="check" size={13} />Ground data: rich</span>
          <span className="chip">Example field · drag to your own</span>
        </div>
      </header>
      <div className="kc-actions">
        <button className="act primary" onClick={p.onDrill} data-testid="drill"><Icon name="cube" size={20} /><span>Drill down</span></button>
        <button className="act" onClick={p.onYear}><Icon name="fields" size={20} /><span>Field’s year</span></button>
        <button className="act" onClick={p.onCompare}><Icon name="compare" size={20} /><span>Compare</span></button>
        <button className="act" onClick={p.onStory}><Icon name="story" size={20} /><span>Story</span></button>
      </div>
      <div className="panel-scroll">
        <div className="kc-now">
          <h3>From orbit · {tLabel(p.t)}</h3>
          <div className="now-grid">
            <div className="now">
              <span className="badge-scale">HLS 30 m</span>
              <b><i className="dot" style={{ background: fs ? CLASS_COLOR[fs.cls] : '#555' }} />{fs ? CLASS_LABEL[fs.cls] : '…'}</b>
              <small>{fs && fs.cls !== 'u' ? `Greenness (NDVI) ${fs.ndvi.toFixed(2)}` : 'No clear view'}</small>
            </div>
            <div className="now">
              <span className="badge-scale coarse">SMAP 9 km</span>
              <b><i className="dot" style={{ background: smap == null ? '#555' : ramp(SMAP_RAMP, smap) }} />{smap == null ? 'No data' : `${ordinal(smap)} pct.`}</b>
              <small>Root-zone soil moisture</small>
            </div>
            <div className="now">
              <span className="badge-scale coarse">GRACE 0.25°</span>
              <b><i className="dot" style={{ background: grace == null ? '#555' : ramp(GRACE_RAMP, grace) }} />{grace == null ? 'No data' : `${ordinal(grace)} pct.`}</b>
              <small>Groundwater storage</small>
            </div>
          </div>
        </div>
        <dl className="facts">
          <div><dt>Field</dt><dd>{loc.area_ha.value.toFixed(0)} ha ({haToAc(loc.area_ha.value).toFixed(0)} acres) · {loc.terrain.note.toLowerCase()}</dd></div>
          <div><dt>Soil</dt><dd>{loc.soil.texture_class}, {loc.soil.drainage_class.toLowerCase()} (SSURGO group {loc.soil.hydrologic_group})</dd></div>
          <div><dt>Water</dt><dd>{loc.water.source === 'surface' ? 'Surface water' : 'Groundwater'} · {loc.water.district}</dd></div>
          <div><dt>Groundwater law</dt><dd>{loc.water.sgma_status.text} {loc.water.sgma_status.verified && <a href={loc.water.sgma_status.url} target="_blank" rel="noreferrer" className="src">source</a>}</dd></div>
          <div><dt>Nearest station</dt><dd>{loc.stations[0].network} {loc.stations[0].id} {loc.stations[0].name}{loc.stations[0].distance_km ? `, ${loc.stations[0].distance_km} km (${(loc.stations[0].distance_km * 0.621).toFixed(0)} mi)` : ''}</dd></div>
        </dl>
        <div className="kc-history">
          <h3>Crop on record <small>USDA Cropland Data Layer</small></h3>
          <div className="cdl-row">
            {YEARS.map((y) => <span key={y} title={`${y}: ${loc.crop_history[y]}`}><i style={{ background: CDL_COLOR(loc.crop_history[y]) }} />{String(y).slice(2)}</span>)}
          </div>
          <p className="muted">{loc.observed_cover.summary}.</p>
        </div>
        <div className="kc-events">
          <h3>What happened here</h3>
          {loc.events.map((e) => (
            <button key={e.date} className="event" onClick={() => p.setT(dateToT(e.date))}>
              <span className={`ev-ico ${e.type}`}><Icon name={e.type === 'atmospheric_river' ? 'drop' : e.type === 'sgma_probation' ? 'info' : 'warn'} size={14} /></span>
              <span className="ev-body">
                <small>{fmtDate(e.date)}{e.end_date ? ` to ${fmtDate(e.end_date)}` : ''}</small>
                <b>{e.title}</b>
                <i>{e.detail}</i>
              </span>
              {e.url && <a className="src" href={e.url} target="_blank" rel="noreferrer" onClick={(ev) => ev.stopPropagation()} title="Open source"><Icon name="link" size={14} /></a>}
            </button>
          ))}
        </div>
        <p className="footnote">This tool supports your judgement and your adviser’s; it does not replace either.</p>
      </div>
    </section>
  );
}

// ---------- "Why not BC yet" ----------
export function BCCard({ bc, onClose, floating }: { bc: BCInfo; onClose?: () => void; floating?: boolean }) {
  return (
    <div className={`bc-card ${floating ? 'glass floating' : ''}`} data-testid="bc-card">
      <div className="bc-head">
        <span className="chip warn"><Icon name="info" size={13} />Out of scope for now</span>
        {onClose && <button className="icon-btn" onClick={onClose}><Icon name="close" size={16} /></button>}
      </div>
      <h3>{bc.title}</h3>
      <p>{bc.intro}</p>
      <ul>
        {bc.lines.map((l) => <li key={l.label}><b>{l.label}</b><span>{l.text}</span></li>)}
      </ul>
      <p className="muted">{bc.limit}</p>
      <span className="bc-next"><Icon name="right" size={14} />{bc.next_step.label} <small>({bc.next_step.ref})</small></span>
    </div>
  );
}

// ---------- Fields list ----------
export function FieldsPanel(p: { locations: Location[]; selectedId: string | null; bc: BCInfo | null; onSelect: (id: string) => void; onClose: () => void }) {
  return (
    <section className="panel glass" data-testid="fields-panel">
      <header className="panel-head"><h2>Pick a field</h2><button className="icon-btn" onClick={p.onClose}><Icon name="close" size={18} /></button></header>
      <div className="panel-scroll">
        {p.locations.map((l) => (
          <button key={l.id} className={`field-card ${l.id} ${p.selectedId === l.id ? 'on' : ''}`} onClick={() => p.onSelect(l.id)}>
            <span className="fc-thumb" />
            <span className="fc-body">
              <small>{l.valley}</small>
              <b>{l.short_name}</b>
              <i>{l.headline}</i>
              <span className="chip good"><Icon name="check" size={12} />Ground data: rich</span>
            </span>
          </button>
        ))}
        <p className="muted pad">Example fields; drag to your own (California only in this prototype).</p>
        {p.bc && <BCCard bc={p.bc} />}
      </div>
    </section>
  );
}

// ---------- Layers drawer ----------
export function LayersDrawer(p: { datasets: Dataset[]; on: Record<string, boolean>; toggle: (id: string) => void; loc: Location | null; metric: 'cover' | 'et'; setMetric: (m: 'cover' | 'et') => void; onClose: () => void }) {
  const fieldKm2 = p.loc ? p.loc.area_ha.value / 100 : 0.6;
  const group = (g: 'field' | 'regional', title: string, sub: string) => (
    <div className="lg">
      <h3>{title}<small>{sub}</small></h3>
      {p.datasets.filter((d) => d.group === g).map((d) => {
        const px = (d.footprint_m / 1000) ** 2;
        const ratio = px >= fieldKm2 ? `1 pixel ≈ ${Math.round(px / fieldKm2).toLocaleString()} fields this size` : `≈ ${Math.round(fieldKm2 / px).toLocaleString()} pixels inside the field`;
        return (
          <label key={d.id} className={`layer ${p.on[d.id] ? 'on' : ''}`}>
            <input type="checkbox" checked={!!p.on[d.id]} onChange={() => p.toggle(d.id)} data-testid={`layer-${d.id}`} />
            <span className="sw" style={p.on[d.id] ? { background: d.color } : undefined} />
            <span className="layer-body">
              <span className="layer-top"><b>{d.name}</b><span className="px" style={{ borderColor: d.color, color: d.color }}>{d.native_scale}</span></span>
              <span className="layer-sees">{d.sees}</span>
              <span className="layer-meta">{ratio} · {d.cadence} · since {d.since}{d.in_stack ? ` · in 3D stack: ${d.in_stack}` : ''}</span>
              {d.caveat && <span className="layer-meta caveat">{d.caveat}</span>}
            </span>
          </label>
        );
      })}
    </div>
  );
  return (
    <aside className="drawer glass" data-testid="layers-drawer">
      <header className="panel-head"><h2>Layers <small>NASA Earth data</small></h2><button className="icon-btn" onClick={p.onClose}><Icon name="close" size={18} /></button></header>
      <div className="panel-scroll">
        <div className="lg">
          <h3>Surface layer shows</h3>
          <div className="seg full">
            <button className={p.metric === 'cover' ? 'on' : ''} onClick={() => p.setMetric('cover')}>Cover</button>
            <button className={p.metric === 'et' ? 'on' : ''} onClick={() => p.setMetric('et')} data-testid="metric-et">Crop water use (ET)</button>
          </div>
        </div>
        {group('field', 'Sees inside your field', 'pixel smaller than the field')}
        {group('regional', 'Sees your district or basin', 'one pixel covers many fields')}
        <div className="scale-ruler">
          <h3>Pixel size, to scale <small>log</small></h3>
          {p.datasets.map((d) => (
            <div key={d.id} className="ruler-row"><span>{d.name}</span><i style={{ width: `${8 + Math.log10(d.footprint_m / 30) * 30}%`, background: d.color }} /><em>{d.native_scale}</em></div>
          ))}
          <div className="ruler-row field"><span>Your field</span><i style={{ width: `${8 + Math.log10(Math.sqrt(fieldKm2) * 1000 / 30) * 30}%` }} /><em>≈ {(Math.sqrt(fieldKm2)).toFixed(1)} km</em></div>
        </div>
        <p className="footnote">Coarse satellites describe weeks and years across the valley. They cannot tell one field from its neighbour.</p>
      </div>
    </aside>
  );
}

// ---------- Trends ----------
function Spark({ values, color, h = 54, bars, min, max, years }: { values: (number | null)[]; color: string; h?: number; bars?: boolean; min?: number; max?: number; years?: boolean }) {
  const W = 340, v = values.filter((x): x is number => x != null);
  const lo = min ?? Math.min(...v), hi = max ?? Math.max(...v);
  const x = (i: number) => (i / (values.length - (bars ? 0 : 1))) * W, y = (val: number) => h - 4 - ((val - lo) / (hi - lo || 1)) * (h - 8);
  let d = '', pen = false;
  values.forEach((val, i) => { if (val == null) { pen = false; return; } d += `${pen ? 'L' : 'M'}${x(i).toFixed(1)},${y(val).toFixed(1)}`; pen = true; });
  return (
    <svg viewBox={`0 0 ${W} ${h + (years ? 14 : 0)}`} className="spark">
      {YEARS.map((yy, i) => <line key={yy} x1={(i / 10) * W} x2={(i / 10) * W} y1="0" y2={h} stroke="rgba(255,255,255,0.08)" />)}
      {bars ? values.map((val, i) => val != null && <rect key={i} x={x(i) + 3} width={W / values.length - 6} y={Math.min(y(val), y(Math.max(lo, 0)))} height={Math.abs(y(val) - y(Math.max(lo, 0)))} fill={color} rx="2" />) : <path d={d} fill="none" stroke={color} strokeWidth="1.8" />}
      {years && YEARS.map((yy, i) => <text key={yy} x={(i / 10) * W + W / 20} y={h + 11} textAnchor="middle" fontSize="9" fill="rgba(255,255,255,0.55)">{String(yy).slice(2)}</text>)}
    </svg>
  );
}
export function TrendsPanel(p: { loc: Location; regional: Regional; onClose: () => void }) {
  const r = p.regional;
  return (
    <section className="panel glass" data-testid="trends-panel">
      <header className="panel-head"><h2>Trends <small>{p.loc.short_name}</small></h2><button className="icon-btn" onClick={p.onClose}><Icon name="close" size={18} /></button></header>
      <div className="panel-scroll">
        <div className="trend"><h3>Root-zone soil moisture <span className="badge-scale coarse">SMAP 9 km</span></h3><p className="muted">Percentile for the time of year</p><Spark values={r.smap_rootzone_pct.values} color="#5ab0ff" min={0} max={100} years /></div>
        <div className="trend"><h3>Groundwater storage <span className="badge-scale coarse">GRACE 0.25°</span></h3><p className="muted">Percentile; gap = no satellite between GRACE and GRACE-FO</p><Spark values={r.grace_gw_pct.values} color="#ff7eb6" min={0} max={100} />
          <p className="muted">Ground check: depth to water in nearby DWR wells (m; deeper is worse)</p><Spark values={r.dwr_well_depth_m.values.map((v) => -(v as number))} color="#f2c14e" h={40} years /></div>
        <div className="trend"><h3>Heatwave days per year <span className="badge-scale coarse">POWER 0.5°</span></h3><Spark values={r.heatwave_days.values} color="#ff6b5e" bars min={0} years /></div>
        <div className="trend"><h3>Summer greenness vs normal <span className="badge-scale">MODIS 250 m</span></h3><Spark values={r.modis_ndvi_anom.values} color="#7ee081" bars min={-2.4} max={1} years /></div>
        <p className="footnote">Trends describe the district or basin, not this field.</p>
      </div>
    </section>
  );
}

// ---------- Brief preview ----------
export function BriefPanel(p: { loc: Location; strategies: RotationStrategy[]; pick: string | null; setPick: (id: string) => void; onClose: () => void }) {
  const s = p.strategies.find((x) => x.id === p.pick) ?? p.strategies.find((x) => !x.is_baseline) ?? p.strategies[0];
  if (!s) return null;
  return (
    <section className="panel glass" data-testid="brief-panel">
      <header className="panel-head"><h2>Rotation brief <small>preview</small></h2><button className="icon-btn" onClick={p.onClose}><Icon name="close" size={18} /></button></header>
      <div className="panel-scroll brief">
        <select value={s.id} onChange={(e) => p.setPick(e.target.value)}>{p.strategies.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</select>
        <h3>{s.name}</h3>
        <div className="month-strip big">{s.month_cover.split('').map((c, i) => <i key={i} title={s.calendar_months[i]} style={{ background: CLASS_COLOR[c as CoverClass] }}>{'JFMAMJJASOND'[i]}</i>)}</div>
        <h4>Why</h4>
        {s.brief.why.map((w) => <p key={w.text} className="why">{w.text} <span className="chip tiny">{w.author} · checked</span></p>)}
        <h4>Funding</h4>
        {s.funding.length ? s.funding.map((f) => <p key={f.program} className="why">{f.program}: rate shown as a range once confirmed locally. <a className="src" href={f.url} target="_blank" rel="noreferrer">NRCS</a></p>) : <p className="muted">No cover-crop practice in this rotation.</p>}
        <h4>Needs local review</h4>
        {s.brief.local_review.map((r) => <label key={r.item} className="review"><input type="checkbox" /><span>{r.item}</span><em className={r.severity}>{r.severity}</em></label>)}
        <button className="btn wide" onClick={() => window.print()}>Print brief</button>
        <p className="footnote">Every alternative rotation needs review by the grower and an adviser before anything is seeded.</p>
      </div>
    </section>
  );
}
