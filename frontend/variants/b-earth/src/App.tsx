import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import MapView, { type MapHandle } from './MapView';
import * as api from './api';
import type { BCInfo, Calendar, CellGrid, CoverClass, Dataset, FieldEvent, Location, NewsItem, Regional, RotationStrategy, Story } from './types';
import { CLASS_COLOR, CLASS_LABEL, ET_RAMP, T_MAX, dateToT, tOf } from './lib';
import Icon from './components/Icons';
import Timeline from './components/Timeline';
import ComparePanel from './components/Compare';
import StoryPanel from './components/Story';
import { BCCard, BriefPanel, FieldsPanel, KnowledgeCard, LayersDrawer, TrendsPanel } from './components/Panels';

type Panel = 'none' | 'fields' | 'trends' | 'compare' | 'brief' | 'story';
const RAIL: { id: Panel | 'search' | 'layers'; icon: string; label: string }[] = [
  { id: 'search', icon: 'search', label: 'Search' },
  { id: 'fields', icon: 'fields', label: 'Fields' },
  { id: 'layers', icon: 'layers', label: 'Layers' },
  { id: 'trends', icon: 'trends', label: 'Trends' },
  { id: 'compare', icon: 'compare', label: 'Compare' },
  { id: 'brief', icon: 'brief', label: 'Brief' },
  { id: 'story', icon: 'story', label: 'Story' },
];

export default function App() {
  const map = useRef<MapHandle>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const [locations, setLocations] = useState<Location[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [bc, setBC] = useState<BCInfo | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [data, setData] = useState<{ id: string; cells: CellGrid; cal: Calendar; regional: Regional; strategies: RotationStrategy[]; news: NewsItem[]; story: Story } | null>(null);
  const [t, setT] = useState(tOf(2024, 19));
  const [playing, setPlaying] = useState(false);
  const [panel, setPanel] = useState<Panel>('none');
  const [cardOpen, setCardOpen] = useState(true);
  const [layersOpen, setLayersOpen] = useState(false);
  const [yearOpen, setYearOpen] = useState(false);
  const [detector, setDetector] = useState<'rule' | 'ml'>('rule');
  const [metric, setMetric] = useState<'cover' | 'et'>('cover');
  const [layersOn, setLayersOn] = useState<Record<string, boolean>>({ hls: true, smap: true, grace: true, imerg: false, modis: false, ecostress: false });
  const [allocation, setAllocation] = useState<Record<string, number>>({});
  const [briefPick, setBriefPick] = useState<string | null>(null);
  const [storyIdx, setStoryIdx] = useState(0);
  const [bcOpen, setBcOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [searchFocus, setSearchFocus] = useState(false);
  const [view, setView] = useState({ zoom: 5.75, pitch: 0, bearing: 0, lat: 37.35, lon: -119.9 });

  useEffect(() => {
    api.getLocations().then((ls) => { setLocations(ls); setAllocation(Object.fromEntries(ls.map((l) => [l.id, l.water.allocation_input.value]))); });
    api.getDatasets().then(setDatasets);
    api.getBC().then(setBC);
  }, []);
  useEffect(() => {
    if (!selectedId) { setData(null); return; }
    let live = true;
    Promise.all([api.getCells(selectedId), api.getCalendar(selectedId), api.getRegional(selectedId), api.getStrategies(selectedId), api.getNews(selectedId), api.getStory(selectedId)]).then(([cells, cal, regional, strategies, news, story]) => live && setData({ id: selectedId, cells, cal, regional, strategies, news, story }));
    return () => { live = false; };
  }, [selectedId]);
  useEffect(() => {
    if (!playing) return;
    const h = setInterval(() => setT((v) => (v >= T_MAX ? 0 : v + 1)), 220);
    return () => clearInterval(h);
  }, [playing]);

  const selected = useMemo(() => locations.find((l) => l.id === selectedId) ?? null, [locations, selectedId]);
  const d = data && data.id === selectedId ? data : null;

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
  const goHome = () => { setSelectedId(null); setPanel('none'); setYearOpen(false); setBcOpen(false); map.current?.flyHome(); };
  const goBC = () => { setBcOpen(true); setPanel('none'); setYearOpen(false); map.current?.flyTo(49.9, -121.0, 6.4); };

  const yearExpanded = yearOpen && !!selected && panel !== 'compare';
  const leftPanel: Panel | 'card' | null = yearExpanded ? null : panel === 'fields' || panel === 'trends' || panel === 'brief' || panel === 'story' ? panel : panel === 'none' && selected && cardOpen ? 'card' : null;
  const leftInset = 64 + (leftPanel ? 396 : 0);
  const rightInset = layersOpen ? 344 : 0;
  const bottomInset = yearExpanded ? 500 : 110;
  const drilled = !!selected && view.zoom > 13.4;
  // keep the stack in view when the year sheet opens or closes over a drilled-in map
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
      ...locations.map((l) => ({ key: l.id, title: l.short_name, sub: `${l.valley} · example field · ground data: rich`, icon: 'fields', go: () => select(l.id) })),
      { key: 'bc', title: 'British Columbia: Salmon River, Sumas Prairie', sub: 'Why not BC yet', icon: 'info', go: goBC },
      { key: 'ca', title: 'California', sub: 'Back to the whole state', icon: 'home', go: goHome },
    ];
    return q ? items.filter((i) => (i.title + i.sub).toLowerCase().includes(q)) : items;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, locations, select]);

  return (
    <div className="app">
      <MapView ref={map} locations={locations} bc={bc} datasets={datasets} selected={selected} cells={d?.cells ?? null} cal={d?.cal ?? null} regional={d?.regional ?? null}
        t={t} detector={detector} metric={metric} layersOn={layersOn} leftInset={leftInset} rightInset={rightInset} bottomInset={bottomInset}
        onSelect={select} onBC={goBC} onView={setView} />

      {/* left icon rail */}
      <nav className="rail glass">
        <button className="rail-logo" onClick={goHome} title="Field Shift: back to California"><span>FS</span></button>
        {RAIL.map((r) => {
          const on = r.id === 'layers' ? layersOpen : r.id === 'search' ? searchFocus : panel === r.id;
          return (
            <button key={r.id} className={`rail-btn ${on ? 'on' : ''}`} data-testid={`rail-${r.id}`} title={r.label}
              onClick={() => (r.id === 'search' ? searchRef.current?.focus() : r.id === 'layers' ? setLayersOpen(!layersOpen) : openPanel(r.id as Panel))}>
              <Icon name={r.icon} size={22} /><span>{r.label}</span>
            </button>
          );
        })}
      </nav>

      {/* search pill */}
      <div className={`search glass ${searchFocus ? 'open' : ''}`}>
        <Icon name="search" size={20} />
        <input ref={searchRef} value={query} onChange={(e) => setQuery(e.target.value)} onFocus={() => setSearchFocus(true)} onBlur={() => setTimeout(() => setSearchFocus(false), 150)} placeholder={selected ? 'Search' : 'Search Field Shift: a field, a valley, a place'} data-testid="search" />
        {selected && <button className="search-chip" onClick={goHome} title="Clear field">{selected.short_name}<Icon name="close" size={14} /></button>}
        {searchFocus && (
          <div className="search-results">
            {results.map((r) => (
              <button key={r.key} onMouseDown={(e) => { e.preventDefault(); r.go(); setQuery(''); searchRef.current?.blur(); }}>
                <span className="sr-ico"><Icon name={r.icon} size={18} /></span><span><b>{r.title}</b><small>{r.sub}</small></span>
              </button>
            ))}
            {results.length === 0 && <p className="muted pad">Only the two California example fields are modelled in this prototype.</p>}
          </div>
        )}
      </div>

      {/* top-right chips */}
      <div className="top-right" style={{ right: 16 + rightInset }}>
        {api.IS_MOCK && <span className="mock-badge" title="Numbers are illustrative and come from src/mock. Events, dates and source links are real and cited." data-testid="mock-badge"><i />Mock data</span>}
        <button className={`pill glass ${layersOpen ? 'on' : ''}`} onClick={() => setLayersOpen(!layersOpen)} data-testid="layers-btn"><Icon name="layers" size={18} />Layers</button>
      </div>

      {/* left column */}
      {leftPanel === 'card' && selected && <KnowledgeCard loc={selected} cal={d?.cal ?? null} regional={d?.regional ?? null} t={t} detector={detector} news={d?.news ?? []} setT={setT}
        onDrill={() => map.current?.flyToField(selected, 'drill')} onYear={() => setYearOpen(true)} onCompare={() => openPanel('compare')} onStory={() => openPanel('story')} onClose={() => setCardOpen(false)} />}
      {leftPanel === 'fields' && <FieldsPanel locations={locations} selectedId={selectedId} bc={bc} onSelect={select} onClose={() => setPanel('none')} />}
      {leftPanel === 'trends' && selected && d && <TrendsPanel loc={selected} regional={d.regional} onClose={() => setPanel('none')} />}
      {leftPanel === 'brief' && selected && d && <BriefPanel loc={selected} strategies={d.strategies} pick={briefPick} setPick={setBriefPick} onClose={() => setPanel('none')} />}
      {leftPanel === 'story' && selected && d && <StoryPanel loc={selected} story={d.story} idx={storyIdx} setIdx={goChapter} cal={d.cal} regional={d.regional} news={d.news} t={t} detector={detector} onClose={() => setPanel('none')} />}
      {selected && !leftPanel && !yearExpanded && panel === 'none' && <button className="reopen pill glass" onClick={() => setCardOpen(true)}><Icon name="info" size={16} />{selected.short_name}</button>}

      {panel === 'compare' && selected && d && <ComparePanel loc={selected} strategies={d.strategies} allocation={allocation[selected.id]} setAllocation={(v) => setAllocation({ ...allocation, [selected.id]: v })}
        onBrief={(id) => { setBriefPick(id); setPanel('brief'); }} onClose={() => setPanel('none')} />}

      {layersOpen && <LayersDrawer datasets={datasets} on={layersOn} toggle={(id) => setLayersOn({ ...layersOn, [id]: !layersOn[id] })} loc={selected} metric={metric} setMetric={setMetric} onClose={() => setLayersOpen(false)} />}

      {/* drill-down HUD */}
      {drilled && panel !== 'compare' && (
        <div className="hud glass" data-testid="hud">
          <span className="hud-title"><Icon name="cube" size={16} />Layer stack</span>
          <div className="seg small">
            <button className={metric === 'cover' ? 'on' : ''} onClick={() => setMetric('cover')}>Cover</button>
            <button className={metric === 'et' ? 'on' : ''} onClick={() => setMetric('et')}>Water use</button>
          </div>
          <div className="hud-legend">
            {metric === 'cover'
              ? (['b', 'p', 'c', 'w'] as CoverClass[]).map((c) => <span key={c}><i style={{ background: CLASS_COLOR[c] }} />{CLASS_LABEL[c]}</span>)
              : <span className="grad"><em>0</em><i style={{ background: `linear-gradient(90deg, ${ET_RAMP.map((s) => s[1]).join(',')})` }} /><em>9 mm/day</em></span>}
            <span className="hud-note">taller = {metric === 'cover' ? 'greener' : 'more water used'}</span>
          </div>
        </div>
      )}
      {!selected && !bcOpen && !nearBC && panel === 'none' && <div className="hint glass">Pick a field, then scroll in to drill down from surface to soil to groundwater</div>}
      {bc && (bcOpen || nearBC) && panel === 'none' && <div className="bc-float" style={{ left: `calc(${leftInset}px + 24px)` }}><BCCard bc={bc} floating onClose={bcOpen ? () => setBcOpen(false) : undefined} /></div>}

      {/* map controls */}
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
    </div>
  );
}
