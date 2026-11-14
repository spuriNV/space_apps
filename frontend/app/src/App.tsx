import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import MapView, { type MapHandle } from './MapView';
import * as api from './api';
import type { BCInfo, CoverClass, Dataset, FieldEvent, Location } from './types';
import { CLASS_COLOR, CLASS_LABEL, ET_RAMP, T_MAX, TODAY_T, dateToT } from './lib';
import type { Daily } from './season';
import Icon from './components/Icons';
import Timeline, { tStart } from './components/Timeline';
import ComingSeason from './components/season/ComingSeason';
import ComparePanel from './components/compare/ComparePanel';
import RotationBrief from './components/brief/RotationBrief';
import { BCCard, LayersDrawer } from './components/Panels';
import { FieldPanel, FieldPicker } from './components/ui/Options';
import { ProvList, acres, county, fieldName, type Step } from './components/ui/shared';

// One look (Extension bulletin, tokens at the top of styles.css). Four screens: pick a field, your field now, coming season, compare and print.
type Panel = 'none' | 'fields' | 'season' | 'compare';
type Tab = 'now' | 'season' | 'year' | 'compare' | 'brief';
const TABS: { id: Tab; label: string; short?: string }[] = [
  { id: 'now', label: 'Field now' },
  { id: 'season', label: 'Coming season' },
  { id: 'year', label: 'This field’s year' },
  { id: 'compare', label: 'Compare' },
  { id: 'brief', label: 'Print for your adviser', short: 'Print' },
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
  const [t, setT] = useState(TODAY_T);
  const [showEarlier, setShowEarlier] = useState(false);
  const [daily, setDaily] = useState<{ id: string; daily: Daily | null; prov: api.Prov } | null>(null);
  const [outlook, setOutlook] = useState<{ id: string; o: api.Outlook } | null>(null);
  const [iss, setISS] = useState<{ id: string; v: Awaited<ReturnType<typeof api.getISS>> } | null>(null);
  const [playing, setPlaying] = useState(false);
  const [panel, setPanel] = useState<Panel>('none');
  const [cardOpen, setCardOpen] = useState(true);
  const [layersOpen, setLayersOpen] = useState(false);
  const [yearOpen, setYearOpen] = useState(false);
  const detector = 'rule' as const;
  const [metric, setMetric] = useState<'cover' | 'et'>('cover');
  const [layersOn, setLayersOn] = useState<Record<string, boolean>>({ hls: true, smap: true, grace: true, imerg: false, modis: false, ecostress: false });
  const [allocation, setAllocation] = useState<Record<string, number>>({});
  const [briefOpen, setBriefOpen] = useState(false);
  const [briefPick, setBriefPick] = useState<string | null>(null);
  const [bcOpen, setBcOpen] = useState(false);
  const [provOpen, setProvOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [switchOpen, setSwitchOpen] = useState(false);
  const [strips, setStrips] = useState<Record<string, Record<number, string>>>({});
  useEffect(() => {
    if (!switchOpen) return;
    const off = (e: MouseEvent) => { if (!(e.target as HTMLElement).closest('.tb-switch')) setSwitchOpen(false); };
    document.addEventListener('mousedown', off);
    return () => document.removeEventListener('mousedown', off);
  }, [switchOpen]);
  const [view, setView] = useState({ zoom: 5.75, pitch: 0, bearing: 0, lat: 37.35, lon: -119.9 });

  useEffect(() => {
    api.getLocations().then(({ locations: ls, prov, live: lv }) => { api.getStrips(ls.map((l) => l.id)).then(setStrips); setLocations(ls); setLocProv(prov); setLive(lv); setAllocation(Object.fromEntries(ls.map((l) => [l.id, l.water.allocation_input.value]))); });
    api.getDatasets().then(setDatasets);
    api.getBC().then(setBC);
  }, []);
  const selected = useMemo(() => locations.find((l) => l.id === selectedId) ?? null, [locations, selectedId]);
  useEffect(() => {
    if (!selected || live == null) { setData(null); return; }
    let ok = true;
    api.getField(selected, live).then((b) => ok && setData(b));
    api.getDaily(selected.id).then((r) => ok && setDaily({ id: selected.id, ...r }));
    api.getOutlook(selected.id, live).then((o) => ok && setOutlook({ id: selected.id, o }));
    api.getISS(selected).then((v) => ok && setISS({ id: selected.id, v }));
    return () => { ok = false; };
  }, [selected, live]);
  // re-score through POST /score when the water allocation changes (engine applies the allocation check)
  const alloc = selected ? allocation[selected.id] : undefined;
  useEffect(() => {
    if (!selected || !live || alloc == null || !data || data.prov.strategies.origin !== 'api') return;
    const h = setTimeout(() => api.scoreStrategies(selected.id, alloc).then((st) => st && setData((d) => {
      if (!d || d.id !== selected.id) return d;
      // POST /score does not carry the OpenET check; keep it from GET /strategies
      const keep = (s: (typeof st)[number]) => { const prev = d.strategies.find((x) => x.id === s.id); return s.water.etc_vs_openet_pct || !prev ? s : { ...s, water: { ...s.water, etc_vs_openet_pct: prev.water.etc_vs_openet_pct, openet_et_mm_season: prev.water.openet_et_mm_season } }; };
      return { ...d, strategies: st.map(keep) };
    })), 450);
    return () => clearTimeout(h);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [alloc, selected, live, data?.id]);
  useEffect(() => {
    if (!playing) return;
    const h = setInterval(() => setT((v) => (v >= T_MAX ? tStart(showEarlier) : Math.max(v + 1, tStart(showEarlier)))), 220);
    return () => clearInterval(h);
  }, [playing, showEarlier]);

  const d = data && data.id === selectedId ? data : null;
  useEffect(() => { (window as unknown as Record<string, unknown>).__app = { setT, select: (id: string) => select(id), ready: !!d }; });
  const dl = daily && daily.id === selectedId ? daily : null;
  const ol = outlook && outlook.id === selectedId ? outlook.o : null;
  const issNow = iss && iss.id === selectedId ? iss.v : null;
  const regional = d?.regional ?? null;
  const regionalLive: api.RegionalLive = d?.regionalLive ?? { smap: false, grace: false, soilSource: null };
  const exampleLimit = !!selected && allocation[selected.id] === api.EXAMPLE_LIMIT[selected.id];
  const prov: api.ProvMap = { ...(selected ? locProv[selected.id] : {}), ...(d?.prov ?? {}), ...(dl ? { daily: dl.prov } : {}), ...(ol ? { outlook_cpc: ol.prov.cpc, outlook_water: ol.prov.water, outlook_alloc: ol.prov.alloc } : {}) };

  const select = useCallback((id: string) => {
    const loc = locations.find((l) => l.id === id);
    if (!loc) return;
    setSelectedId(id); setCardOpen(true); setBcOpen(false);
    setPanel((p) => (p === 'fields' ? 'none' : p));
    map.current?.flyToField(loc, 'card');
  }, [locations]);

  const openPanel = (id: Panel) => {
    if (id !== 'fields' && !selected) { setPanel('fields'); return; }
    if (id === 'none') { setPanel('none'); setCardOpen(true); setYearOpen(false); return; }
    setPanel((p) => (p === id ? 'none' : id));
    setYearOpen(false);
  };
  const goHome = () => { setSelectedId(null); setPanel('none'); setYearOpen(false); setBcOpen(false); setBriefOpen(false); map.current?.flyHome(); };
  const goBC = () => { setBcOpen(true); setPanel('none'); setYearOpen(false); map.current?.flyTo(49.9, -121.0, 6.4); };
  const onStep = (s: Step) => {
    if (!selected) return;
    if (s === 'drill') { setPanel('none'); map.current?.flyToField(selected, 'drill'); }
    else if (s === 'year') { setPanel('none'); setYearOpen(true); }
    else if (s === 'compare') openPanel('compare');
    else if (s === 'season') openPanel('season');
    else { setBriefPick(null); setBriefOpen(true); }
  };

  const yearExpanded = yearOpen && !!selected && panel !== 'compare' && panel !== 'season';
  // left column: a tool panel, else the field panel, else (nothing picked yet) the "Pick your field" list
  const toolPanel = panel === 'fields' ? panel : null;
  const leftPanel = yearExpanded ? null : toolPanel ?? (panel === 'none' && selected && cardOpen ? 'card' : panel === 'none' && !selected && !bcOpen ? 'fields' : null);
  const leftInset = leftPanel === 'fields' ? 464 : leftPanel ? 412 : 0;
  const rightInset = layersOpen ? 344 : 0;
  const bottomInset = yearExpanded ? (showEarlier ? 520 : 330) : 110;
  const drilled = !!selected && view.zoom > 13.4;
  useEffect(() => { if (selected && view.zoom > 13.2) map.current?.flyToField(selected, yearExpanded ? 'year' : 'drill'); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [yearExpanded, showEarlier]);
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
  const tabOn = (id: Tab) => !!selected && (id === 'brief' ? briefOpen : id === 'year' ? yearExpanded : id === 'now' ? panel === 'none' && !yearExpanded && leftPanel === 'card' : panel === id);
  const onTab = (id: Tab) => {
    setSwitchOpen(false);
    if (!selected) { setPanel('none'); setSwitchOpen(true); return; }
    if (id === 'now') openPanel('none');
    else if (id === 'year') onStep('year');
    else if (id === 'brief') onStep('brief');
    else openPanel(id);
  };

  return (
    <div className="app">
      <MapView ref={map} locations={locations} bc={bc} datasets={datasets} selected={selected} cells={d?.cells ?? null} cal={d?.cal ?? null} regional={regional}
        t={t} detector={detector} metric={metric} regionalLive={regionalLive} layersOn={layersOn} leftInset={leftInset} rightInset={rightInset} bottomInset={bottomInset}
        onSelect={select} onBC={goBC} onView={setView} />

      <header className="topbar" data-testid="topbar">
        <button className="tb-brand" onClick={goHome} title="Back to all of California">CropLytics</button>
        <div className={`tb-switch ${switchOpen ? 'open' : ''}`}>
          <button className="tb-field" onClick={() => { setSwitchOpen(!switchOpen); setTimeout(() => searchRef.current?.focus(), 0); }} data-testid="field-switch" aria-expanded={switchOpen}>
            <span><small>{selected ? `${county(selected)} County, ${acres(selected)} acres` : 'No field picked'}</small><b>{selected ? fieldName(selected) : 'Pick your field'}</b></span>
            <Icon name="down" size={18} />
          </button>
          {switchOpen && (
            <div className="tb-menu" data-testid="field-menu">
              <div className="tb-search"><Icon name="search" size={16} />
                <input ref={searchRef} value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => { if (e.key === 'Escape') setSwitchOpen(false); if (e.key === 'Enter' && results[0]) { results[0].go(); setQuery(''); setSwitchOpen(false); } }} placeholder="Find a field by town, county or crop" data-testid="search" />
              </div>
              {results.map((r) => (
                <button key={r.key} className={r.key === selectedId ? 'on' : ''} onClick={() => { r.go(); setQuery(''); setSwitchOpen(false); }} data-testid={`switch-${r.key}`}>
                  <b>{r.title}</b><small>{r.sub}</small>
                </button>
              ))}
              {results.length === 0 && <p className="muted pad">Only the two California fields are set up so far.</p>}
            </div>
          )}
        </div>
        <nav className="tb-tabs" aria-label="Sections">
          {TABS.map((tb) => (
            <button key={tb.id} className={tabOn(tb.id) ? 'on' : ''} onClick={() => onTab(tb.id)} data-testid={`tab-${tb.id}`} disabled={!selected && tb.id !== 'now'} title={selected ? undefined : 'Pick a field first'}><span className="tb-long">{tb.label}</span>{tb.short && <span className="tb-short">{tb.short}</span>}</button>
          ))}
        </nav>
        <div className="tb-right">
          {live != null && (
            <button className={`data-ind ${live ? 'live' : 'example'}`} onClick={() => setProvOpen(!provOpen)} data-testid="data-indicator"
              title={live ? 'Real outputs from the CropLytics API; parts marked "example numbers" are still illustrative' : 'API not reachable: showing the bundled example data'}>
              <i />{live ? 'Live data' : 'Example data only'}{selected && mockParts > 0 && <em>{mockParts} parts are examples</em>}
            </button>
          )}
          <button className={`tb-layers ${layersOpen ? 'on' : ''}`} onClick={() => setLayersOpen(!layersOpen)} data-testid="layers-btn"><Icon name="layers" size={16} />Map layers</button>
          {provOpen && (
            <div className="prov-pop glass">
              <h4>{live ? 'Where each part of this view comes from' : 'Example data: the CropLytics API is not reachable'}</h4>
              {selected ? <ProvList prov={prov} /> : <p className="muted">Pick a field to see where each part of the view comes from.</p>}
            </div>
          )}
        </div>
      </header>

      {leftPanel === 'card' && selected && <FieldPanel loc={selected} prov={prov} cal={d?.cal ?? null} regional={regional} regionalLive={regionalLive} strategies={d?.strategies ?? null} allocation={allocation[selected.id]} exampleLimit={exampleLimit} daily={dl?.daily ?? null}
        nasa={d?.nasa ?? null} nasaNow={d?.nasaNow ?? null} iss={issNow} loading={!d || !dl}
        t={t} setT={setT} events={events} onStep={onStep} onClose={() => setCardOpen(false)} />}
      {leftPanel === 'fields' && <FieldPicker locations={locations} live={live} strips={strips} selectedId={selectedId} onSelect={select} onBC={goBC} onClose={panel === 'fields' ? () => setPanel('none') : undefined} />}
      {selected && !leftPanel && !yearExpanded && panel === 'none' && <button className="reopen pill glass" onClick={() => setCardOpen(true)}><Icon name="info" size={16} />{fieldName(selected)}</button>}

      {panel === 'season' && selected && d && <ComingSeason nasaNow={d.nasaNow} regional={regional} regionalLive={regionalLive} loc={selected} outlook={ol} cal={d.cal} daily={dl?.daily ?? null} strategies={d.strategies} allocation={allocation[selected.id]} exampleLimit={exampleLimit} prov={prov} onCompare={() => setPanel('compare')} onClose={() => setPanel('none')} />}
      {panel === 'compare' && selected && d && <ComparePanel loc={selected} strategies={d.strategies} daily={dl?.daily ?? null} allocation={allocation[selected.id]} exampleLimit={exampleLimit} live={!!live} cal={d.cal} setAllocation={(v) => setAllocation({ ...allocation, [selected.id]: v })}
        onBrief={(id) => { setBriefPick(id); setBriefOpen(true); }} onClose={() => setPanel('none')} />}

      {layersOpen && <LayersDrawer datasets={datasets} on={layersOn} toggle={(id) => setLayersOn({ ...layersOn, [id]: !layersOn[id] })} loc={selected} metric={metric} setMetric={setMetric} onClose={() => setLayersOpen(false)} />}

      {drilled && panel !== 'compare' && panel !== 'season' && (
        <div className="hud glass" data-testid="hud">
          <span className="hud-title"><Icon name="cube" size={16} />Under the field</span>
          <div className="seg small">
            <button className={metric === 'cover' ? 'on' : ''} onClick={() => setMetric('cover')}>Ground cover</button>
            <button className={metric === 'et' ? 'on' : ''} onClick={() => setMetric('et')}>Water use</button>
          </div>
          <div className="hud-legend">
            {metric === 'cover'
              ? (['b', 'p', 'c', 'w'] as CoverClass[]).map((c) => <span key={c}><i style={{ background: CLASS_COLOR[c] }} />{({ b: 'Bare', p: 'Thin', c: 'Crop', w: 'Flooded' } as Record<string, string>)[c]}</span>)
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

      <Timeline t={t} setT={setT} playing={playing} setPlaying={setPlaying} loc={selected} cal={d?.cal ?? null} daily={dl?.daily ?? null} ml={d?.ml ?? null} prov={d?.prov.calendar} events={events}
        showEarlier={showEarlier} setShowEarlier={setShowEarlier} expanded={yearExpanded} setExpanded={(b) => { setYearOpen(b); if (b && (panel === 'compare' || panel === 'season')) setPanel('none'); }} />

      {briefOpen && selected && d && <RotationBrief loc={selected} strategies={d.strategies} pick={briefPick} setPick={setBriefPick} allocation={allocation[selected.id]} exampleLimit={exampleLimit} prov={prov} outlook={ol} nasaNow={d.nasaNow} cal={d.cal} daily={dl?.daily ?? null} onClose={() => setBriefOpen(false)} />}
    </div>
  );
}
