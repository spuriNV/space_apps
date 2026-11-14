import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import MapView, { type MapHandle } from './MapView';
import * as api from './api';
import type { BCInfo, CoverClass, Dataset, FieldEvent, Location } from './types';
import { CLASS_COLOR, CLASS_LABEL, ET_RAMP, T_MAX, dateToT, tOf } from './lib';
import Icon from './components/Icons';
import Timeline from './components/Timeline';
import ComparePanel from './components/compare/ComparePanel';
import StoryPanel from './components/Story';
import RotationBrief from './components/brief/RotationBrief';
import { BCCard, LayersDrawer, TrendsPanel } from './components/Panels';
import { FieldPanel, FieldPicker } from './components/ui/Options';
import { ProvList, acres, county, fieldName, type Step } from './components/ui/shared';

/** ?theme=1 survey sheet (default) · 2 extension bulletin · 3 field desk. One field panel for all three; see .claude/skills/fieldshift-visual-design. */
export const THEME = (() => { const v = Number(new URLSearchParams(window.location.search).get('theme')); return v === 2 || v === 3 ? v : 1; })();
document.documentElement.dataset.theme = String(THEME);

type Panel = 'none' | 'fields' | 'trends' | 'compare' | 'story';
const RAIL: { id: Panel | 'search' | 'layers' | 'brief'; icon: string; label: string }[] = [
  { id: 'search', icon: 'search', label: 'Find' },
  { id: 'fields', icon: 'fields', label: 'Fields' },
  { id: 'layers', icon: 'layers', label: 'Map layers' },
  { id: 'trends', icon: 'trends', label: 'Water trends' },
  { id: 'compare', icon: 'compare', label: 'Rotations' },
  { id: 'brief', icon: 'brief', label: 'Print' },
  { id: 'story', icon: 'story', label: 'Story' },
];

export default function App() {
  const map = useRef<MapHandle>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const [locations, setLocations] = useState<Location[]>([]);
  const [locProv, setLocProv] = useState<Record<string, api.ProvMap>>({});
  const [live, setLive] = useState<boolean | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [bc, setBC] = useState<BCInfo | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [data, setData] = useState<api.FieldBundle | null>(null);
  const [t, setT] = useState(tOf(2023, 10));
  const [playing, setPlaying] = useState(false);
  const [panel, setPanel] = useState<Panel>('none');
  const [cardOpen, setCardOpen] = useState(true);
  const [layersOpen, setLayersOpen] = useState(false);
  const [yearOpen, setYearOpen] = useState(false);
  const [detector, setDetector] = useState<'rule' | 'ml'>('rule');
  const [metric, setMetric] = useState<'cover' | 'et'>('cover');
  const [layersOn, setLayersOn] = useState<Record<string, boolean>>({ hls: true, smap: true, grace: true, imerg: false, modis: false, ecostress: false });
  const [allocation, setAllocation] = useState<Record<string, number>>({});
  const [briefOpen, setBriefOpen] = useState(false);
  const [briefPick, setBriefPick] = useState<string | null>(null);
  const [storyIdx, setStoryIdx] = useState(0);
  const [bcOpen, setBcOpen] = useState(false);
  const [provOpen, setProvOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [searchFocus, setSearchFocus] = useState(false);
  const [view, setView] = useState({ zoom: 5.75, pitch: 0, bearing: 0, lat: 37.35, lon: -119.9 });

  useEffect(() => {
    api.getLocations().then(({ locations: ls, prov, live: lv }) => { setLocations(ls); setLocProv(prov); setLive(lv); setAllocation(Object.fromEntries(ls.map((l) => [l.id, l.water.allocation_input.value]))); });
    api.getDatasets().then(setDatasets);
    api.getBC().then(setBC);
  }, []);
  const selected = useMemo(() => locations.find((l) => l.id === selectedId) ?? null, [locations, selectedId]);
  useEffect(() => {
    if (!selected || live == null) { setData(null); return; }
    let ok = true;
    api.getField(selected, live).then((b) => ok && setData(b));
    return () => { ok = false; };
  }, [selected, live]);
  // re-score through POST /score when the water allocation changes (engine applies the allocation check)
  const alloc = selected ? allocation[selected.id] : undefined;
  useEffect(() => {
    if (!selected || !live || alloc == null || !data || data.prov.strategies.origin !== 'api') return;
    const h = setTimeout(() => api.scoreStrategies(selected.id, alloc).then((st) => st && setData((d) => (d && d.id === selected.id ? { ...d, strategies: st } : d))), 450);
    return () => clearTimeout(h);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [alloc, selected, live, data?.id]);
  useEffect(() => {
    if (!playing) return;
    const h = setInterval(() => setT((v) => (v >= T_MAX ? 0 : v + 1)), 220);
    return () => clearInterval(h);
  }, [playing]);

  const d = data && data.id === selectedId ? data : null;
  useEffect(() => { (window as unknown as Record<string, unknown>).__app = { setT, select: (id: string) => select(id), ready: !!d }; });
  const prov: api.ProvMap = { ...(selected ? locProv[selected.id] : {}), ...(d?.prov ?? {}) };

  const select = useCallback((id: string) => {
    const loc = locations.find((l) => l.id === id);
    if (!loc) return;
    setSelectedId(id); setCardOpen(true); setBcOpen(false); setStoryIdx(0);
    setPanel((p) => (p === 'fields' ? 'none' : p));
    map.current?.flyToField(loc, 'card');
  }, [locations]);

  const openPanel = (id: Panel) => {
    if (id !== 'fields' && id !== 'none' && !selected) { setPanel('fields'); return; }
    setPanel((p) => (p === id ? 'none' : id));
    setYearOpen(false);
    if (id === 'story' && selected && d) goChapter(storyIdx);
  };
  const goChapter = (i: number) => {
    if (!selected || !d) return;
    const ch = d.story.chapters[i];
    setStoryIdx(i); setPlaying(false); setT(dateToT(ch.date));
    map.current?.flyToField(selected, ch.camera === 'drill' ? 'story' : 'card');
  };
  const goHome = () => { setSelectedId(null); setPanel('none'); setYearOpen(false); setBcOpen(false); setBriefOpen(false); map.current?.flyHome(); };
  const goBC = () => { setBcOpen(true); setPanel('none'); setYearOpen(false); map.current?.flyTo(49.9, -121.0, 6.4); };
  const onStep = (s: Step) => {
    if (!selected) return;
    if (s === 'drill') { setPanel('none'); map.current?.flyToField(selected, 'drill'); }
    else if (s === 'year') { setPanel('none'); setYearOpen(true); }
    else if (s === 'compare') openPanel('compare');
    else { setBriefPick(null); setBriefOpen(true); }
  };

  const yearExpanded = yearOpen && !!selected && panel !== 'compare';
  // left column: a tool panel, else the field panel, else (nothing picked yet) the "Pick your field" list
  const toolPanel = panel === 'trends' || panel === 'story' || panel === 'fields' ? panel : null;
  const leftPanel = yearExpanded ? null : toolPanel ?? (panel === 'none' && selected && cardOpen ? 'card' : panel === 'none' && !selected && !bcOpen ? 'fields' : null);
  const leftInset = 64 + (leftPanel ? 396 : 0);
  const rightInset = layersOpen ? 344 : 0;
  const bottomInset = yearExpanded ? 500 : 110;
  const drilled = !!selected && view.zoom > 13.4;
  useEffect(() => { if (selected && view.zoom > 13.2) map.current?.flyToField(selected, yearExpanded ? 'year' : 'drill'); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [yearExpanded]);
  const nearBC = view.lat > 46.2 && view.zoom > 4.5;

  const events: FieldEvent[] = useMemo(() => {
    if (selected) return selected.events;
    const all = locations.flatMap((l) => l.events);
    return (['drought_fallow', 'atmospheric_river', 'sgma_probation'] as const).map((k) => all.find((e) => e.type === k)).filter((e): e is FieldEvent => !!e);
  }, [locations, selected]);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    const items = [
      ...locations.map((l) => ({ key: l.id, title: fieldName(l), sub: `${county(l)} County · ${acres(l)} acres${l.dwr_id ? ' · state field no. ' + l.dwr_id : ''}`, icon: 'fields', go: () => select(l.id) })),
      { key: 'bc', title: 'Sumas Prairie, British Columbia', sub: 'Not set up yet: why', icon: 'info', go: goBC },
      { key: 'ca', title: 'California', sub: 'Back to the whole state', icon: 'home', go: goHome },
    ];
    return q ? items.filter((i) => (i.title + i.sub).toLowerCase().includes(q)) : items;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, locations, select]);

  const mockParts = Object.values(prov).filter((p) => p.origin === 'mock').length;

  return (
    <div className="app">
      <MapView ref={map} locations={locations} bc={bc} datasets={datasets} selected={selected} cells={d?.cells ?? null} cal={d?.cal ?? null} regional={d?.regional ?? null}
        t={t} detector={detector} metric={metric} layersOn={layersOn} leftInset={leftInset} rightInset={rightInset} bottomInset={bottomInset}
        onSelect={select} onBC={goBC} onView={setView} />

      <nav className="rail glass">
        <button className="rail-logo" onClick={goHome} title="Field Shift: back to all of California"><span>Field<br />Shift</span></button>
        {RAIL.map((r) => {
          const on = r.id === 'layers' ? layersOpen : r.id === 'search' ? searchFocus : r.id === 'brief' ? briefOpen : panel === r.id;
          return (
            <button key={r.id} className={`rail-btn ${on ? 'on' : ''}`} data-testid={`rail-${r.id}`} title={r.label}
              onClick={() => (r.id === 'search' ? searchRef.current?.focus() : r.id === 'layers' ? setLayersOpen(!layersOpen) : r.id === 'brief' ? (selected ? setBriefOpen(true) : openPanel('fields')) : openPanel(r.id as Panel))}>
              <Icon name={r.icon} size={20} /><span>{r.label}</span>
            </button>
          );
        })}
      </nav>

      <div className={`search glass ${searchFocus ? 'open' : ''}`}>
        <Icon name="search" size={18} />
        <input ref={searchRef} value={query} onChange={(e) => setQuery(e.target.value)} onFocus={() => setSearchFocus(true)} onBlur={() => setTimeout(() => setSearchFocus(false), 150)} placeholder="Find a field by town, county or crop" data-testid="search" />
        {searchFocus && (
          <div className="search-results">
            {results.map((r) => (
              <button key={r.key} onMouseDown={(e) => { e.preventDefault(); r.go(); setQuery(''); searchRef.current?.blur(); }}>
                <span className="sr-ico"><Icon name={r.icon} size={16} /></span><span><b>{r.title}</b><small>{r.sub}</small></span>
              </button>
            ))}
            {results.length === 0 && <p className="muted pad">Only the two California fields are set up so far.</p>}
          </div>
        )}
      </div>

      <div className="top-right" style={{ right: 16 + rightInset }}>
        {live != null && (
          <button className={`data-ind ${live ? 'live' : 'example'}`} onClick={() => setProvOpen(!provOpen)} data-testid="data-indicator"
            title={live ? 'Real outputs from the Field Shift API and backend files; parts marked "example numbers" are still illustrative' : 'API not reachable: showing the bundled example data'}>
            <i />{live ? 'Live data' : 'Example data only'}{selected && mockParts > 0 && <em>{mockParts} parts are examples</em>}
          </button>
        )}
        <button className={`pill glass ${layersOpen ? 'on' : ''}`} onClick={() => setLayersOpen(!layersOpen)} data-testid="layers-btn"><Icon name="layers" size={16} />Map layers</button>
        {provOpen && (
          <div className="prov-pop glass">
            <h4>{live ? 'Where each part of this view comes from' : 'Example data: the Field Shift API is not reachable'}</h4>
            {selected ? <ProvList prov={prov} /> : <p className="muted">Pick a field to see where each part of the view comes from.</p>}
          </div>
        )}
      </div>

      {leftPanel === 'card' && selected && <FieldPanel loc={selected} prov={prov} cal={d?.cal ?? null} regional={d?.regional ?? null} strategies={d?.strategies ?? null} allocation={allocation[selected.id]}
        t={t} setT={setT} detector={detector} events={events} onStep={onStep} onClose={() => setCardOpen(false)} />}
      {leftPanel === 'fields' && <FieldPicker locations={locations} selectedId={selectedId} onSelect={select} onBC={goBC} onClose={panel === 'fields' ? () => setPanel('none') : undefined} />}
      {leftPanel === 'trends' && selected && d && <TrendsPanel loc={selected} regional={d.regional} onClose={() => setPanel('none')} />}
      {leftPanel === 'story' && selected && d && <StoryPanel loc={selected} story={d.story} idx={storyIdx} setIdx={goChapter} cal={d.cal} regional={d.regional} news={d.news} t={t} detector={detector} onClose={() => setPanel('none')} />}
      {selected && !leftPanel && !yearExpanded && panel === 'none' && <button className="reopen pill glass" onClick={() => setCardOpen(true)}><Icon name="info" size={16} />{fieldName(selected)}</button>}

      {panel === 'compare' && selected && d && <ComparePanel loc={selected} strategies={d.strategies} allocation={allocation[selected.id]} setAllocation={(v) => setAllocation({ ...allocation, [selected.id]: v })}
        onBrief={(id) => { setBriefPick(id); setBriefOpen(true); }} onClose={() => setPanel('none')} />}

      {layersOpen && <LayersDrawer datasets={datasets} on={layersOn} toggle={(id) => setLayersOn({ ...layersOn, [id]: !layersOn[id] })} loc={selected} metric={metric} setMetric={setMetric} onClose={() => setLayersOpen(false)} />}

      {drilled && panel !== 'compare' && (
        <div className="hud glass" data-testid="hud">
          <span className="hud-title"><Icon name="cube" size={16} />Under the field</span>
          <div className="seg small">
            <button className={metric === 'cover' ? 'on' : ''} onClick={() => setMetric('cover')}>Ground cover</button>
            <button className={metric === 'et' ? 'on' : ''} onClick={() => setMetric('et')}>Water use</button>
          </div>
          <div className="hud-legend">
            {metric === 'cover'
              ? (['b', 'p', 'c', 'w', 'u'] as CoverClass[]).map((c) => <span key={c}><i style={{ background: CLASS_COLOR[c] }} />{c === 'u' ? 'No clear pixel' : CLASS_LABEL[c]}</span>)
              : <span className="grad"><em>0</em><i style={{ background: `linear-gradient(90deg, ${ET_RAMP.map((s) => s[1]).join(',')})` }} /><em>9 mm/day</em></span>}
            <span className="hud-note">taller = {metric === 'cover' ? 'greener (NDVI)' : 'more water used'}</span>
          </div>
        </div>
      )}
            {bc && (bcOpen || nearBC) && panel === 'none' && <div className="bc-float" style={{ left: `calc(${leftInset}px + 24px)` }}><BCCard bc={bc} floating onClose={bcOpen ? () => setBcOpen(false) : undefined} /></div>}

      <div className="controls" style={{ right: 16 + rightInset, bottom: bottomInset + 14 }}>
        <button className="ctl glass" onClick={goHome} title="Whole of California"><Icon name="home" size={18} /></button>
        <button className="ctl glass" onClick={() => map.current?.resetNorth()} title="Reset north"><span style={{ transform: `rotate(${-view.bearing - 45}deg)`, display: 'flex' }}><Icon name="compass" size={20} /></span></button>
        <button className="ctl glass text" onClick={() => map.current?.toggle3D()} title="Tilt" data-testid="tilt">{view.pitch > 5 ? '2D' : '3D'}</button>
        <div className="ctl-group glass">
          <button onClick={() => map.current?.zoomBy(1)} title="Zoom in"><Icon name="plus" size={18} /></button>
          <button onClick={() => map.current?.zoomBy(-1)} title="Zoom out"><Icon name="minus" size={18} /></button>
        </div>
      </div>

      <Timeline t={t} setT={setT} playing={playing} setPlaying={setPlaying} loc={selected} cal={d?.cal ?? null} news={d?.news ?? []} events={events}
        detector={detector} setDetector={setDetector} expanded={yearExpanded} setExpanded={(b) => { setYearOpen(b); if (b && panel === 'compare') setPanel('none'); }} />

      {briefOpen && selected && d && <RotationBrief loc={selected} strategies={d.strategies} pick={briefPick} setPick={setBriefPick} allocation={allocation[selected.id]} prov={prov} onClose={() => setBriefOpen(false)} />}
    </div>
  );
}
