import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Map as MLMap } from 'maplibre-gl';
import { IS_MOCK, getBcCard, getFieldYear, getLocation, getLocations, getNews, getStrategies, getTrends, getZones } from './api';
import type { LocationId, MeasureKey, TrendLayer } from './types';
import MapView, { flyHome, flyToDrill, measureDomain, type CameraInfo, type Selected } from './components/MapView';
import PlacePanel, { isWide, type Tab } from './components/PlacePanel';
import Icon from './components/Icon';
import { COVER_COLORS, COVER_LABELS, ESRI_TILE, MONTH_LETTERS, RAMPS, dateToWeek, fmt, fmtDate, mmToIn, rampCss, weekLabel } from './util';

type ChipId = 'bare' | 'water' | 'soil' | 'gw' | 'crops';
const CHIPS: { id: ChipId; label: string; icon: string }[] = [
  { id: 'bare', label: 'Bare periods', icon: 'bare' },
  { id: 'water', label: 'Water use', icon: 'drop' },
  { id: 'soil', label: 'Soil moisture', icon: 'leaf' },
  { id: 'gw', label: 'Groundwater', icon: 'waves' },
  { id: 'crops', label: 'Crop history', icon: 'history' },
];
const MEASURES: { id: MeasureKey; label: string; lo: string; hi: string }[] = [
  { id: 'ndvi', label: 'Cover', lo: 'thin', hi: 'dense' },
  { id: 'et_mm', label: 'Water use', lo: 'less', hi: 'more' },
  { id: 'stress', label: 'Stress', lo: 'none', hi: 'hotspot' },
  { id: 'bare_days', label: 'Bare days', lo: 'few', hi: 'many' },
];
const REPLAY_YEARS = [2021, 2022, 2023, 2024, 2025];

function readHash(): { field: Selected; tab: Tab } {
  const h = new URLSearchParams(window.location.hash.slice(1));
  const f = h.get('field');
  const ok = f === 'bc' || getLocations().some((l) => l.id === f);
  const t = h.get('tab') as Tab | null;
  return { field: ok ? (f as Selected) : null, tab: t && ['overview', 'year', 'compare', 'sources'].includes(t) ? t : 'overview' };
}

export default function App() {
  const locations = useMemo(getLocations, []);
  const bc = useMemo(getBcCard, []);
  const init = useMemo(readHash, []);
  const [selected, setSelected] = useState<Selected>(init.field);
  const [tab, setTab] = useState<Tab>(init.tab);
  const [basemap, setBasemap] = useState<'streets' | 'satellite'>('streets');
  const [chip, setChip] = useState<ChipId | null>(null);
  const [measure, setMeasure] = useState<MeasureKey>('ndvi');
  const [tilt3d, setTilt3d] = useState(true);
  const [footprints, setFootprints] = useState(true);
  const [cam, setCam] = useState<CameraInfo>({ zoom: 5.8, pitch: 0, bearing: 0, nearId: null, drill: 0 });
  const [replay, setReplay] = useState({ on: false, year: 2023, week: 0 });
  const [playing, setPlaying] = useState(false);
  const [query, setQuery] = useState('');
  const [focus, setFocus] = useState(false);
  const [brief, setBrief] = useState<string | null>(null);
  const [snack, setSnack] = useState<string | null>(null);
  const [alloc, setAlloc] = useState<Record<string, number>>(() => Object.fromEntries(locations.map((l) => [l.id, l.water.allocation_input.value])));
  const mapRef = useRef<MLMap | null>(null);

  const field = selected && selected !== 'bc' ? selected : null;
  const wide = !!field && isWide(tab);
  const panelW = selected ? (wide ? 928 : 408) : 0;
  const inField = cam.nearId && cam.zoom >= 12.6 ? cam.nearId : null;
  const trendLayer: TrendLayer | null = chip === 'soil' ? 'smap_anomaly' : chip === 'gw' ? 'grace_gw_pct' : null;

  const toast = useCallback((m: string) => { setSnack(m); window.setTimeout(() => setSnack((s) => (s === m ? null : s)), 3600); }, []);
  const select = useCallback((id: Selected) => {
    setSelected(id); setTab('overview'); setFocus(false); setQuery('');
    if (!id) { setReplay((r) => ({ ...r, on: false })); setPlaying(false); }
  }, []);
  const onCamera = useCallback((c: CameraInfo) => setCam((p) => (p.zoom === c.zoom && p.pitch === c.pitch && p.bearing === c.bearing && p.nearId === c.nearId && p.drill === c.drill ? p : c)), []);
  const onReady = useCallback((m: MLMap) => { mapRef.current = m; }, []);

  useEffect(() => {
    window.history.replaceState(null, '', selected ? `#field=${selected}${tab !== 'overview' ? `&tab=${tab}` : ''}` : window.location.pathname);
  }, [selected, tab]);
  useEffect(() => {
    const k = (e: KeyboardEvent) => { if (e.key === 'Escape') { if (brief) setBrief(null); else if (focus) setFocus(false); } };
    window.addEventListener('keydown', k);
    return () => window.removeEventListener('keydown', k);
  }, [brief, focus]);

  // replay clock
  useEffect(() => {
    if (!playing) return;
    const t = window.setInterval(() => setReplay((r) => (r.week >= 51 ? (setPlaying(false), r) : { ...r, week: Math.min(51, r.week + 0.25) })), 90);
    return () => window.clearInterval(t);
  }, [playing]);

  const drill = (id: LocationId) => { if (tab !== 'overview' && tab !== 'sources') setTab('overview'); window.setTimeout(() => mapRef.current && flyToDrill(mapRef.current, id), 60); };
  const startReplay = (id: LocationId, year: number) => {
    setReplay({ on: true, year, week: 0 }); setPlaying(false); setTilt3d(true);
    if (cam.drill < 0.9 || cam.nearId !== id) drill(id); else if (tab !== 'overview') setTab('overview');
  };
  const onChip = (c: ChipId) => {
    const next = chip === c ? null : c;
    setChip(next);
    if (!next) return;
    if (c === 'soil' || c === 'gw') return;
    if (!field) { toast('Pick a field first: Colusa rice or Tulare/Kings forage.'); setFocus(true); return; }
    if (c === 'bare') { setMeasure('bare_days'); setTab('year'); }
    if (c === 'water') { setMeasure('et_mm'); setTab('compare'); }
    if (c === 'crops') { setTab('overview'); window.setTimeout(() => document.getElementById('crop-history')?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 80); }
  };
  const share = () => { navigator.clipboard?.writeText(window.location.href).catch(() => {}); toast('Link to this field copied'); };

  const suggestions = useMemo(() => {
    const all = [
      ...locations.map((l) => ({ id: l.id as Selected, icon: 'place', title: l.short_name, sub: `${l.place_line} · Ground data: rich` })),
      { id: 'bc' as Selected, icon: 'info', title: bc.name, sub: `${bc.place_line} · not modelled` },
    ];
    const q = query.trim().toLowerCase();
    return q ? all.filter((s) => (s.title + s.sub).toLowerCase().includes(q)) : all;
  }, [query, locations, bc]);

  const selName = selected === 'bc' ? bc.name : field ? getLocation(field).short_name : '';
  const legendId = replay.on && field ? field : inField;
  const tileSat = ESRI_TILE(6, 10, 24);

  return (
    <div className="app">
      {selected && (
        <PlacePanel
          selected={selected} tab={tab} onTab={setTab} onClose={() => select(null)}
          onDrill={() => field && drill(field)} onBrief={() => field && setBrief(getStrategies(field)[1].id)} onShare={share}
          allocation={field ? alloc[field] : 0} onAllocation={(v) => field && setAlloc((a) => ({ ...a, [field]: v }))}
          onReplayOnMap={(y) => field && startReplay(field, y)}
        />
      )}

      {/* search pill (floats above panel, like the Maps omnibox) */}
      <div className={`search${focus ? ' search-open' : ''}`}>
        <button className="icon-btn logo" title="Field Shift: back to California" onClick={() => { select(null); mapRef.current && flyHome(mapRef.current); }}>
          <svg width="24" height="24" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="#188038" /><path d="M7 15.500c0-4.500 3.500-7.500 10-8-.500 6.500-3.500 10-8 10-.700 0-1.400-.200-2-.500l5-5.500-5.800 4.600c-.100-.200-.200-.400-.200-.600z" fill="#fff" /></svg>
        </button>
        <input
          value={focus ? query : selName || query}
          placeholder="Search Field Shift"
          onFocus={() => { setFocus(true); setQuery(''); }}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && suggestions[0]) select(suggestions[0].id); }}
          aria-label="Search fields"
        />
        <button className="icon-btn" aria-label="Search" onClick={() => setFocus(true)}><Icon name="search" size={22} color="#5f6368" /></button>
        {selected && <><span className="search-div" /><button className="icon-btn" aria-label="Close place" onClick={() => select(null)}><Icon name="close" size={22} color="#5f6368" /></button></>}
        {focus && (
          <div className="suggest">
            {suggestions.map((s) => (
              <button key={String(s.id)} className="suggest-row" onMouseDown={(e) => { e.preventDefault(); select(s.id); }}>
                <span className={`suggest-icon${s.id === 'bc' ? ' grey' : ''}`}><Icon name={s.icon} size={20} /></span>
                <span><b>{s.title}</b><small>{s.sub}</small></span>
              </button>
            ))}
            <div className="suggest-row disabled"><span className="suggest-icon grey"><Icon name="pen" size={18} /></span><span><b>Draw your own field</b><small>California only · coming after the hackathon build</small></span></div>
          </div>
        )}
      </div>
      {focus && <div className="scrim" onClick={() => setFocus(false)} />}

      <div className="map-wrap" style={{ left: panelW }}>
        <MapView
          selected={selected} basemap={basemap} trendLayer={trendLayer} measure={measure} replay={replay}
          tilt3d={tilt3d} footprints={footprints} onSelect={select} onCamera={onCamera} onReady={onReady}
        />

        {!wide && (
          <div className="chips" style={{ left: selected ? 16 : 420 }}>
            {CHIPS.map((c) => (
              <button key={c.id} className={`chip${chip === c.id ? ' chip-on' : ''}`} onClick={() => onChip(c.id)} aria-pressed={chip === c.id}>
                <Icon name={c.icon} size={18} />{c.label}
              </button>
            ))}
          </div>
        )}

        <div className="top-right">
          {IS_MOCK && <span className="mock-badge" title="All field numbers are illustrative. Dates, events and links are from the project spec."><Icon name="info" size={15} />Mock data</span>}
        </div>

        {/* legends, right side */}
        {!wide && (
          <div className="right-rail">
            {legendId && <DrillLegend id={legendId} measure={measure} onMeasure={(m) => { setMeasure(m); setReplay((r) => ({ ...r, on: false })); setPlaying(false); }} drill={cam.drill} tilt3d={tilt3d}
              footprints={footprints} onFootprints={setFootprints} replayOn={replay.on} onReplay={() => { setSelected(legendId); startReplay(legendId, 2023); }} />}
            {trendLayer && !legendId && <TrendLegend id={field ?? 'car_colusa_rice'} layer={trendLayer} />}
          </div>
        )}

        {field && !wide && !replay.on && cam.drill === 0 && cam.zoom > 9 && (
          <div className="hint"><span className="mouse"><i /></span>Scroll in on the field to see it in 3D</div>
        )}

        {replay.on && field && !wide && (
          <ReplayBar id={field} replay={replay} playing={playing}
            onPlay={() => { if (replay.week >= 51) setReplay((r) => ({ ...r, week: 0 })); setPlaying((p) => !p); }}
            onWeek={(w) => { setPlaying(false); setReplay((r) => ({ ...r, week: w })); }}
            onYear={(y) => setReplay((r) => ({ ...r, year: y, week: Math.min(r.week, 51) }))}
            onClose={() => { setPlaying(false); setReplay((r) => ({ ...r, on: false })); }} />
        )}

        {/* bottom-left: layers thumbnail */}
        <button className="layers" onClick={() => setBasemap(basemap === 'streets' ? 'satellite' : 'streets')} aria-label="Switch map type">
          {basemap === 'streets' ? <img src={tileSat} alt="" /> : <span className="layers-map" />}
          <span className="layers-label"><Icon name="layers" size={14} color="#fff" />{basemap === 'streets' ? 'Satellite' : 'Map'}</span>
        </button>

        {/* bottom-right: camera controls */}
        <div className="controls">
          <button className={`ctl ctl-text${tilt3d && cam.pitch > 0 ? ' on' : ''}`} title={tilt3d ? 'Switch to flat view' : 'Switch to 3D view'} onClick={() => setTilt3d(!tilt3d)}>{tilt3d ? '2D' : '3D'}</button>
          <button className="ctl" title="Reset north" onClick={() => mapRef.current?.easeTo({ bearing: 0 })}>
            <span style={{ transform: `rotate(${-cam.bearing}deg)`, display: 'inline-flex' }}>
              <svg width="22" height="22" viewBox="0 0 24 24"><path d="M12 2 8 12h8z" fill="#ea4335" /><path d="M12 22 8 12h8z" fill="#bdc1c6" /></svg>
            </span>
          </button>
          <div className="ctl-stack">
            <button className="ctl" title="Zoom in" onClick={() => mapRef.current?.zoomIn()}><Icon name="add" size={22} color="#5f6368" /></button>
            <span />
            <button className="ctl" title="Zoom out" onClick={() => mapRef.current?.zoomOut()}><Icon name="remove" size={22} color="#5f6368" /></button>
          </div>
        </div>
      </div>

      {brief && field && <BriefDialog fieldId={field} strategyId={brief} onPick={setBrief} onClose={() => setBrief(null)} />}
      {snack && <div className="snack">{snack}</div>}
    </div>
  );
}

// ------------------------------------------------------------------ drill-down legend
function DrillLegend(p: { id: LocationId; measure: MeasureKey; onMeasure: (m: MeasureKey) => void; drill: number; tilt3d: boolean; footprints: boolean; onFootprints: (v: boolean) => void; replayOn: boolean; onReplay: () => void }) {
  const zones = getZones(p.id);
  const loc = getLocation(p.id);
  const m = MEASURES.find((x) => x.id === p.measure)!;
  const dom = measureDomain(p.id, p.measure);
  const meta = zones.measures[p.measure];
  const unit = p.measure === 'et_mm' ? (v: number) => `${fmt(v)} mm (${fmt(mmToIn(v), 0)} in)` : p.measure === 'ndvi' ? (v: number) => v.toFixed(2) : (v: number) => fmt(v, p.measure === 'stress' ? 1 : 0);
  // to-scale inset: 9 km SMAP square = 76 px
  const S = 76, k = S / 9000;
  const smap = zones.footprints.smap_9km.geometry.coordinates[0];
  const [lon0, lat0] = smap[0], [lon1, lat1] = smap[2];
  const proj = ([lo, la]: number[]) => `${((lo - lon0) / (lon1 - lon0)) * S},${S - ((la - lat0) / (lat1 - lat0)) * S}`;
  const n = zones.cells.features.length;
  return (
    <div className="legend-card">
      <div className="legend-title"><Icon name="cube" size={18} color="#1a73e8" />Inside the field<span>30 m cells</span></div>
      {p.replayOn ? (
        <div className="legend-note strong">Replaying cover week by week. Blue = standing water.</div>
      ) : (
        <div className="measure-grid" role="radiogroup" aria-label="Measure">
          {MEASURES.map((x) => <button key={x.id} role="radio" aria-checked={p.measure === x.id} className={p.measure === x.id ? 'on' : ''} onClick={() => p.onMeasure(x.id)}>{x.label}</button>)}
        </div>
      )}
      <div className="ramp" style={{ background: rampCss(RAMPS[p.replayOn ? 'ndvi' : p.measure]) }} />
      <div className="ramp-labels"><span>{p.replayOn ? 'bare' : `${unit(dom[0])} · ${m.lo}`}</span><span>{p.replayOn ? 'dense cover' : `${m.hi} · ${unit(dom[1])}`}</span></div>
      <div className="legend-note">{p.tilt3d ? (p.drill > 0 ? 'Taller and darker = more.' : 'Scroll in: cells rise as you get closer.') : 'Flat view. Press 3D to raise the cells.'} {p.replayOn ? 'HLS, 30 m.' : `${meta.label}: ${meta.dataset.toUpperCase()}.`}</div>
      {!p.replayOn && p.measure === 'stress' && <div className="legend-note warn">{zones.hotspot_note}</div>}
      <div className="px">
        <svg width={S + 2} height={S + 2} viewBox={`-1 -1 ${S + 2} ${S + 2}`}>
          <rect x="0" y="0" width={S} height={S} fill="rgba(26,115,232,.08)" stroke="#1a73e8" strokeWidth="1.5" strokeDasharray="4 3" />
          <polygon points={loc.geometry.coordinates[0].map(proj).join(' ')} fill="#34a853" stroke="#188038" strokeWidth="1" />
          <rect x={S * 0.62} y={S * 0.62} width={250 * k} height={250 * k} fill="#e37400" />
        </svg>
        <div className="px-text">
          <div className="px-h">Pixel size, to scale</div>
          <div><i className="k k-smap" />SMAP soil moisture: <b>9 km</b>, one value for the whole square</div>
          <div><i className="k k-modis" />MODIS: <b>250 m</b> (the orange speck)</div>
          <div><i className="k k-field" />HLS and OpenET: <b>30 m</b>, {fmt(n)} values in this field</div>
        </div>
      </div>
      <div className="legend-foot">
        <label className="check"><input type="checkbox" checked={p.footprints} onChange={(e) => p.onFootprints(e.target.checked)} />Pixel outlines on map</label>
        {!p.replayOn && <button className="pill-btn blue" onClick={p.onReplay}><Icon name="play" size={16} />Replay a year</button>}
      </div>
    </div>
  );
}

function TrendLegend({ id, layer }: { id: LocationId; layer: TrendLayer }) {
  const t = getTrends(id);
  const meta = t.layers[layer];
  const series = t.series[layer];
  const W = 268, H = 64;
  const vals = series.map((s) => s.value);
  const lo = Math.min(...vals), hi = Math.max(...vals);
  const x = (i: number) => (i / (series.length - 1)) * (W - 8) + 4;
  const y = (v: number) => H - 6 - ((v - lo) / (hi - lo || 1)) * (H - 14);
  return (
    <div className="legend-card">
      <div className="legend-title"><Icon name={layer === 'smap_anomaly' ? 'leaf' : 'waves'} size={18} color="#1a73e8" />{layer === 'smap_anomaly' ? 'Soil moisture' : 'Groundwater'}<span>{meta.year}</span></div>
      <div className="legend-note">{meta.label}. Shown around both example fields.</div>
      <div className="ramp" style={{ background: rampCss(RAMPS[layer]) }} />
      <div className="ramp-labels"><span>{layer === 'smap_anomaly' ? 'drier than usual' : 'lowest on record'}</span><span>{layer === 'smap_anomaly' ? 'wetter' : 'normal'}</span></div>
      <div className="px-h" style={{ marginTop: 10 }}>{getLocation(id).short_name}: {series[0].year}–{series[series.length - 1].year}</div>
      <svg width={W} height={H} className="spark">
        {t.event_markers.map((e) => { const i = series.findIndex((s) => s.year === e.year); return i < 0 ? null : <g key={e.year}><line x1={x(i)} x2={x(i)} y1={2} y2={H - 2} stroke="#ea4335" strokeDasharray="2 2" /><text x={x(i) - 3} y={10} textAnchor="end" fontSize="9" fill="#c5221f">{e.label}</text></g>; })}
        <polyline points={series.map((s, i) => `${x(i)},${y(s.value)}`).join(' ')} fill="none" stroke="#1a73e8" strokeWidth="2" strokeLinejoin="round" />
      </svg>
      <div className="legend-note warn">{meta.note ?? 'One SMAP pixel is 9 km wide: it describes the valley, not one field.'}</div>
    </div>
  );
}

// ------------------------------------------------------------------ replay scrubber (design idea)
function ReplayBar(p: { id: LocationId; replay: { year: number; week: number }; playing: boolean; onPlay: () => void; onWeek: (w: number) => void; onYear: (y: number) => void; onClose: () => void }) {
  const fy = getFieldYear(p.id);
  const row = fy.years.find((y) => y.year === p.replay.year)!;
  const news = getNews(p.id).filter((n) => n.date.startsWith(String(p.replay.year)));
  const W = 560, H = 58;
  const x = (w: number) => (w / 51) * W;
  const median = Array.from({ length: 52 }, (_, w) => { const v = fy.years.map((y) => y.ndvi[w]).sort((a, b) => a - b); return (v[4] + v[5]) / 2; });
  const yN = (v: number) => H - 4 - v * (H - 10);
  const maxRain = Math.max(60, ...row.rain_mm);
  const w = Math.floor(p.replay.week);
  const cls = row.rule[w];
  const near = news.find((n) => Math.abs(dateToWeek(n.date) - p.replay.week) <= 2.5);
  return (
    <div className="replay">
      <div className="replay-top">
        <button className="play" onClick={p.onPlay} aria-label={p.playing ? 'Pause' : 'Play'}><Icon name={p.playing ? 'pause' : 'play'} size={24} color="#fff" /></button>
        <div className="replay-when">
          <b>{weekLabel(p.replay.year, w)}</b>
          <span><i className="sw" style={{ background: COVER_COLORS[cls] }} />{COVER_LABELS[cls]} · field NDVI {row.ndvi[w].toFixed(2)} · rain {row.rain_mm[w]} mm ({fmt(mmToIn(row.rain_mm[w]), 1)} in)</span>
        </div>
        <div className="seg small" role="group" aria-label="Year">
          {REPLAY_YEARS.map((y) => <button key={y} className={p.replay.year === y ? 'on' : ''} onClick={() => p.onYear(y)}>{y}</button>)}
        </div>
        <button className="icon-btn" onClick={p.onClose} aria-label="Close replay"><Icon name="close" size={20} color="#5f6368" /></button>
      </div>
      <div className="replay-track" style={{ width: W }}>
        <svg width={W} height={H}>
          {row.rule.split('').map((c, i) => <rect key={i} x={x(i) - W / 104} y={H - 5} width={W / 52 + 0.5} height={5} fill={COVER_COLORS[c]} />)}
          {row.rain_mm.map((mm, i) => mm > 0 && <rect key={i} x={x(i) - 3} y={0} width={6} height={(mm / maxRain) * 24} fill="#8ab4f8" rx="1" />)}
          <polyline points={median.map((v, i) => `${x(i)},${yN(v)}`).join(' ')} fill="none" stroke="#9aa0a6" strokeWidth="1.5" strokeDasharray="3 3" />
          <polyline points={row.ndvi.map((v, i) => `${x(i)},${yN(v)}`).join(' ')} fill="none" stroke="#188038" strokeWidth="2.2" strokeLinejoin="round" />
          {news.map((n) => <g key={n.date + n.title}><line x1={x(dateToWeek(n.date))} x2={x(dateToWeek(n.date))} y1={0} y2={H - 5} stroke="#ea4335" strokeWidth="1.5" /><circle cx={x(dateToWeek(n.date))} cy={6} r={5} fill="#ea4335" stroke="#fff" strokeWidth="1.5" /></g>)}
          <line x1={x(p.replay.week)} x2={x(p.replay.week)} y1={0} y2={H} stroke="#202124" strokeWidth="2" />
          <circle cx={x(p.replay.week)} cy={yN(row.ndvi[w])} r={5} fill="#fff" stroke="#202124" strokeWidth="2" />
        </svg>
        <input type="range" min={0} max={51} step={0.25} value={p.replay.week} onChange={(e) => p.onWeek(Number(e.target.value))} aria-label="Week of year" />
        <div className="replay-months">{MONTH_LETTERS.map((m, i) => <span key={i}>{['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][i]}</span>)}</div>
      </div>
      <div className="replay-foot">
        <span className="rk"><i style={{ background: '#188038' }} />This year's cover</span>
        <span className="rk"><i className="dash" />Usual year (2016–2025)</span>
        <span className="rk"><i style={{ background: '#8ab4f8', height: 8 }} />Weekly rain</span>
        <span className="rk"><i className="dotred" />News</span>
        {near ? <span className="replay-news"><b>{fmtDate(near.date)}</b> {near.title}</span> : <span className="replay-news muted">{row.cdl_class ? `Crop map says: ${row.cdl_class}` : 'Crop map for this year not out yet'}</span>}
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ brief dialog (light version of the printable brief)
function BriefDialog({ fieldId, strategyId, onPick, onClose }: { fieldId: LocationId; strategyId: string; onPick: (id: string) => void; onClose: () => void }) {
  const all = getStrategies(fieldId).filter((s) => !s.is_baseline);
  const s = all.find((x) => x.id === strategyId) ?? all[0];
  const loc = getLocation(fieldId);
  return (
    <div className="modal-scrim" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Rotation brief">
        <div className="modal-head">
          <div><div className="card-k">Rotation brief · {loc.short_name}</div><h2>{s.name}</h2></div>
          <button className="icon-btn" onClick={onClose} aria-label="Close"><Icon name="close" size={22} color="#5f6368" /></button>
        </div>
        <div className="seg small">{all.map((a) => <button key={a.id} className={a.id === s.id ? 'on' : ''} onClick={() => onPick(a.id)}>{a.short}</button>)}</div>
        <div className="mstrip big">{s.month_cover.split('').map((c, i) => <span key={i} style={{ background: COVER_COLORS[c] }} title={s.month_labels[i]}>{MONTH_LETTERS[i]}</span>)}</div>
        <div className="section-title">Why consider it</div>
        <ul className="why">{s.brief.why.map((w) => <li key={w.text}>{w.text}<span className="signal-chip">checked against data</span></li>)}</ul>
        <div className="section-title">Needs local review</div>
        <div className="review">{s.brief.local_review.map((r) => <label key={r.item}><input type="checkbox" />{r.item}<span className={`sev sev-${r.severity}`}>{r.severity}</span></label>)}</div>
        <div className="section-title">Funding</div>
        <div className="muted">{s.funding[0].program}: rate shown as a range once confirmed locally. <a href={s.funding[0].url} target="_blank" rel="noreferrer">NRCS EQIP</a></div>
        <div className="modal-foot"><span className="muted">Supports, does not replace, advice from your adviser. Review before anything is seeded.</span><button className="pill-btn blue" onClick={() => window.print()}>Print</button></div>
      </div>
    </div>
  );
}
