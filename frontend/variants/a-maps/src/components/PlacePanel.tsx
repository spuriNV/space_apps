import { useMemo } from 'react';
import { getBcCard, getLocation, getNews, getSources, getZones } from '../api';
import type { Geometry, LocationId } from '../types';
import { ESRI_TILE, fmt, fmtDate, haToAc, MM_PER_AFAC, tileXY } from '../util';
import Icon from './Icon';
import YearTab from './YearTab';
import CompareTab from './CompareTab';

export type Tab = 'overview' | 'year' | 'compare' | 'sources';
export const TABS: { id: Tab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'year', label: 'Year' },
  { id: 'compare', label: 'Compare' },
  { id: 'sources', label: 'Sources' },
];
export const isWide = (t: Tab) => t === 'year' || t === 'compare';

/** Hero image: a mosaic of Esri World Imagery tiles around the field, with the boundary drawn on top. */
function Hero({ lon, lat, z, geometry, height = 216, muted }: { lon: number; lat: number; z: number; geometry?: Geometry; height?: number; muted?: boolean }) {
  const W = 408;
  const c = tileXY(lon, lat, z);
  const tiles = [];
  const x0 = Math.floor(c.x - W / 512), x1 = Math.floor(c.x + W / 512);
  const y0 = Math.floor(c.y - height / 512), y1 = Math.floor(c.y + height / 512);
  for (let x = x0; x <= x1; x++) for (let y = y0; y <= y1; y++) tiles.push({ x, y, left: (x - c.x) * 256 + W / 2, top: (y - c.y) * 256 + height / 2 });
  const pts = geometry?.coordinates[0].map(([lo, la]) => { const t = tileXY(lo, la, z); return `${(t.x - c.x) * 256 + W / 2},${(t.y - c.y) * 256 + height / 2}`; }).join(' ');
  return (
    <div className={`hero${muted ? ' hero-muted' : ''}`} style={{ height }}>
      {tiles.map((t) => <img key={`${t.x}-${t.y}`} src={ESRI_TILE(z, t.x, t.y)} style={{ left: t.left, top: t.top }} alt="" draggable={false} />)}
      {pts && <svg width={W} height={height}><polygon points={pts} fill="rgba(255,255,255,0.10)" stroke="#fff" strokeWidth="2.5" strokeLinejoin="round" /></svg>}
      <div className="hero-shade" />
      <span className="hero-credit">Esri World Imagery</span>
    </div>
  );
}

const CROP_COLORS: Record<string, string> = { Rice: '#00a8e6', 'Fallow/Idle': '#bfbf7a', Alfalfa: '#ff9fbd', 'Winter wheat / Corn': '#e9c400', Cotton: '#ff5f4f' };

function InfoRow({ icon, children, sub }: { icon: string; children: React.ReactNode; sub?: React.ReactNode }) {
  return (
    <div className="info-row">
      <span className="info-icon"><Icon name={icon} size={22} color="#1a73e8" /></span>
      <div><div className="info-main">{children}</div>{sub && <div className="info-sub">{sub}</div>}</div>
    </div>
  );
}

function Overview({ id, onDrill, onTab }: { id: LocationId; onDrill: () => void; onTab: (t: Tab) => void }) {
  const loc = getLocation(id);
  const zones = getZones(id);
  const news = getNews(id);
  const years = Object.keys(loc.crop_history);
  const alloc = loc.water.allocation_input.value;
  return (
    <div className="tab-body">
      <div className="lede">
        <b>Now:</b> {loc.baseline_summary}. {loc.observed_cover.summary} (satellite cover record 2016–2025).
      </div>
      <button className="drill-card" onClick={onDrill}>
        <span className="drill-thumb"><Icon name="cube" size={26} color="#fff" /></span>
        <span className="drill-text"><b>See inside this field in 3D</b><span>{fmt(zones.cells.features.length)} cells at 30 m. Scroll in on the field, or click here.</span></span>
        <Icon name="right" size={22} color="#5f6368" />
      </button>
      <div className="divider" />
      <InfoRow icon="square" sub="Example field; drag to your own (California only)">{fmt(loc.area_ha.value, 1)} ha ({fmt(haToAc(loc.area_ha.value))} acres)</InfoRow>
      <InfoRow icon="terrain" sub={`${loc.soil.drainage_class}, hydrologic group ${loc.soil.hydrologic_group}. ${loc.terrain.note}`}>{loc.soil.muname}</InfoRow>
      <InfoRow icon="drop" sub={`${loc.water.district} · allocation set to ${fmt(alloc, 1)} acre-ft/acre (${fmt(alloc * MM_PER_AFAC)} mm)`}>
        {loc.water.source === 'surface' ? 'Surface water' : 'Groundwater-dependent'}
      </InfoRow>
      <InfoRow icon="waves" sub={<a href={loc.water.sgma_status.url} target="_blank" rel="noreferrer">SGMA status source</a>}>{loc.water.sgma_status.text}</InfoRow>
      <InfoRow icon="station" sub={loc.stations.slice(1).map((s) => s.name).join(' · ')}>
        {loc.stations[0].network} {loc.stations[0].id} {loc.stations[0].name}, {loc.stations[0].distance_km} km away
      </InfoRow>
      <div className="divider" />
      <div className="section-title" id="crop-history">Crop history <span>USDA Cropland Data Layer 2008–2024</span></div>
      <div className="cdl-strip">
        {years.map((y) => <span key={y} title={`${y}: ${loc.crop_history[y]}`} style={{ background: CROP_COLORS[loc.crop_history[y]] ?? '#ccc' }} />)}
      </div>
      <div className="cdl-axis"><span>2008</span><span>2012</span><span>2016</span><span>2020</span><span>2024</span></div>
      <div className="cdl-legend">
        {[...new Set(Object.values(loc.crop_history))].map((c) => <span key={c}><i style={{ background: CROP_COLORS[c] ?? '#ccc' }} />{c}</span>)}
      </div>
      <div className="divider" />
      <div className="section-title">In the news <span>next to the satellite signal</span></div>
      {news.map((n) => (
        <div className="news-row" key={n.date + n.title}>
          <span className="news-date">{fmtDate(n.date)}</span>
          <div>
            <div className="news-title">{n.url ? <a href={n.url} target="_blank" rel="noreferrer">{n.title}</a> : n.title}</div>
            <div className="news-meta">{n.source}{n.signal && <span className="signal-chip">{n.signal.label}: {n.signal.value_pct}</span>}{!n.verified && <span className="u-chip">unverified</span>}</div>
          </div>
        </div>
      ))}
      <button className="text-btn" onClick={() => onTab('year')}>See these on the field's year</button>
      <div className="footnote">This tool supports a conversation between a grower and an adviser. It does not replace local advice.</div>
    </div>
  );
}

const SCALE: Record<string, [string, string, string]> = {
  hls: ['HLS (Landsat + Sentinel-2)', '30 m', 'field'], s2: ['Sentinel-2 L2A', '10 m', 'field'], openet: ['OpenET measured ET', '30 m', 'field'], cdl: ['USDA Cropland Data Layer', '30 m', 'field'],
  ecostress: ['ECOSTRESS land-surface temperature', '70 m', 'field'], modis: ['MODIS vegetation index', '250 m', 'neighbourhood'], smap_l3: ['SMAP soil moisture', '9 km', 'valley'],
  imerg: ['GPM IMERG rain', '~10 km', 'valley'], power: ['NASA POWER weather', '~50 km', 'region'], grace: ['GRACE / GRACE-FO groundwater', '~300 km signal', 'basin'],
  cimis: ['CIMIS weather station', 'point', 'ground'], dwr_wells: ['DWR groundwater wells', 'point', 'ground'], cdec: ['CDEC reservoir storage', 'point', 'ground'], rma: ['USDA RMA cause of loss', 'county', 'county'],
};
function Sources({ id }: { id: LocationId }) {
  const loc = getLocation(id);
  const src = getSources();
  return (
    <div className="tab-body">
      <div className="lede">What each dataset can and cannot see. Coarse datasets describe the valley, not this field.</div>
      <div className="src-list">
        {loc.datasets.filter((d) => SCALE[d]).map((d) => (
          <div className="src-row" key={d}>
            <div><div className="info-main">{SCALE[d][0]}</div><div className="info-sub">{SCALE[d][1]}</div></div>
            <span className={`scale-badge scale-${SCALE[d][2]}`}>{SCALE[d][2]}-scale</span>
          </div>
        ))}
      </div>
      <div className="divider" />
      <div className="section-title">Cited sources</div>
      {['nasa_eo_rice', 'farmprogress_rice', 'uc_rice_blog', 'uc_alfalfa', 'fao56_table12', 'ssurgo_sda', 'cimis', 'eqip_340'].map((k) => (
        <a className="src-link" key={k} href={src[k].url ?? '#'} target="_blank" rel="noreferrer"><Icon name="open" size={16} />{src[k].title}</a>
      ))}
      <div className="footnote">Prototype: field numbers on this page are illustrative mock data. Dates, events and links are from the project spec.</div>
    </div>
  );
}

function BcPanel({ onClose }: { onClose: () => void }) {
  const bc = useMemo(getBcCard, []);
  return (
    <>
      <Hero lon={bc.centroid.lon} lat={bc.centroid.lat} z={11} muted />
      <div className="place-head">
        <h1>{bc.name}</h1>
        <div className="place-sub">{bc.place_line}</div>
        <div className="badges"><span className="badge badge-amber">Ground data: thin</span><span className="badge badge-grey">Not modelled</span></div>
      </div>
      <div className="divider" />
      <div className="tab-body">
        <div className="lede">{bc.summary}</div>
        {bc.reasons.map((r) => <InfoRow key={r.title} icon="warning" sub={r.text}>{r.title}</InfoRow>)}
        <div className="callout">{bc.limits_line}</div>
        <div className="section-title">{bc.next_step.label}</div>
        <div className="chip-wrap">{bc.next_step.items.map((i) => <span className="mini-chip" key={i}>{i}</span>)}</div>
        <div className="divider" />
        <div className="section-title">Where the problem started</div>
        {bc.news.map((n) => (
          <div className="news-row" key={n.title}><span className="news-date">{fmtDate(n.date)}</span>
            <div><div className="news-title"><a href={n.url!} target="_blank" rel="noreferrer">{n.title}</a></div><div className="news-meta">{n.source}</div></div></div>
        ))}
        <button className="text-btn" onClick={onClose}>Back to the California fields</button>
      </div>
    </>
  );
}

interface Props {
  selected: LocationId | 'bc';
  tab: Tab;
  onTab: (t: Tab) => void;
  onClose: () => void;
  onDrill: () => void;
  onBrief: () => void;
  onShare: () => void;
  allocation: number;
  onAllocation: (v: number) => void;
  onReplayOnMap: (year: number) => void;
}

export default function PlacePanel(p: Props) {
  if (p.selected === 'bc') return <aside className="panel"><div className="panel-scroll"><BcPanel onClose={p.onClose} /></div></aside>;
  const loc = getLocation(p.selected);
  const wide = isWide(p.tab);
  const actions: { icon: string; label: string; primary?: boolean; on: () => void }[] = [
    { icon: 'compare', label: 'Compare rotations', primary: true, on: () => p.onTab('compare') },
    { icon: 'calendar', label: "Field's year", on: () => p.onTab('year') },
    { icon: 'description', label: 'Brief', on: p.onBrief },
    { icon: 'share', label: 'Share', on: p.onShare },
  ];
  return (
    <aside className={`panel${wide ? ' panel-wide' : ''}`}>
      <div className="panel-scroll">
        {!wide && <Hero lon={loc.centroid.lon} lat={loc.centroid.lat} z={15} geometry={loc.geometry} />}
        {wide ? (
          <div className="wide-head">
            <div>
              <h1>{loc.name}</h1>
              <div className="place-sub">{loc.place_line} · {fmt(loc.area_ha.value, 1)} ha ({fmt(haToAc(loc.area_ha.value))} acres)</div>
            </div>
            <div className="badges"><span className="badge badge-green"><Icon name="check" size={14} />Ground data: rich</span><span className="badge badge-grey">Example field</span></div>
          </div>
        ) : (
          <>
            <div className="place-head">
              <h1>{loc.name}</h1>
              <div className="place-sub">{loc.place_line}</div>
              <div className="badges"><span className="badge badge-green"><Icon name="check" size={14} />Ground data: rich</span><span className="badge badge-grey">Example field</span></div>
            </div>
            <div className="actions">
              {actions.map((a) => (
                <button key={a.label} className={`action${a.primary ? ' action-primary' : ''}`} onClick={a.on}>
                  <span className="action-circle"><Icon name={a.icon} size={20} /></span>
                  <span>{a.label}</span>
                </button>
              ))}
            </div>
          </>
        )}
        <div className="tabs" role="tablist">
          {TABS.map((t) => <button key={t.id} role="tab" aria-selected={p.tab === t.id} className={p.tab === t.id ? 'tab tab-on' : 'tab'} onClick={() => p.onTab(t.id)}>{t.label}</button>)}
          {wide && <span className="tabs-right"><button className="pill-btn" onClick={p.onBrief}><Icon name="description" size={16} />Brief</button><button className="pill-btn" onClick={p.onShare}><Icon name="share" size={16} />Share</button></span>}
        </div>
        {p.tab === 'overview' && <Overview id={loc.id} onDrill={p.onDrill} onTab={p.onTab} />}
        {p.tab === 'year' && <YearTab id={loc.id} onReplayOnMap={p.onReplayOnMap} />}
        {p.tab === 'compare' && <CompareTab id={loc.id} allocation={p.allocation} onAllocation={p.onAllocation} onBrief={p.onBrief} />}
        {p.tab === 'sources' && <Sources id={loc.id} />}
      </div>
    </aside>
  );
}
