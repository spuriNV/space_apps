import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import MapView, { type MapHandle } from './MapView';
import * as api from './api';
import type { BCInfo, CoverClass, Dataset, FieldEvent, Location } from './types';
import { CLASS_COLOR, CLASS_LABEL, ET_RAMP, MONTHS, RECENT_FROM, T_MAX, TODAY_T, YEARS, dateToT, tLabel, tOf, yearOf, dekadOf } from './lib';
import type { Daily } from './season';
import Icon from './components/Icons';
import YearSheet from './components/year/YearSheet';
import { calSource } from './components/ui/shared';
const tStart = (earlier: boolean) => tOf(earlier ? YEARS[0] : RECENT_FROM, 0);
import ComingSeason from './components/season/ComingSeason';
import ComparePanel from './components/compare/ComparePanel';
import RotationBrief from './components/brief/RotationBrief';
import { BCCard, LayersDrawer } from './components/Panels';
import { FieldPanel, FieldPicker } from './components/ui/Options';
import { setGlossary } from './components/ui/What';
import { DetailCtx, useDetailState } from './components/ui/Detail';
import { ProvList, acres, county, fieldName, type Step } from './components/ui/shared';

// One look (Extension bulletin, tokens at the top of styles.css). Four screens: pick a field, your field now, coming season, compare and print.
type Panel = 'none' | 'fields' | 'season' | 'compare';
type Tab = 'now' | 'season' | 'year' | 'compare' | 'brief';
/** Quick dates in the grower's words for the "Viewing" control. */
const QUICK: { label: string; sub: string; t: number }[] = [
  { label: 'Today', sub: 'mid Nov 2026', t: TODAY_T },
  { label: 'Last summer', sub: 'Jul 2026', t: tOf(2026, 19) },
  { label: 'Last spring', sub: 'Apr 2026', t: tOf(2026, 10) },
  { label: '2023 floods', sub: 'Mar 2023', t: tOf(2023, 7) },
  { label: '2022 drought', sub: 'Jul 2022', t: tOf(2022, 19) },
];
const MOB: Record<string, string> = { now: 'Now', season: 'Season', year: 'Year', compare: 'Compare' };
/** Phone width: the field panel becomes a bottom sheet and the sections a bottom tab bar. */
function usePhone() {
  const q = '(max-width: 640px)';
  const [m, setM] = useState(() => typeof window !== 'undefined' && window.matchMedia(q).matches);
  useEffect(() => { const mq = window.matchMedia(q); const f = () => setM(mq.matches); mq.addEventListener('change', f); return () => mq.removeEventListener('change', f); }, []);
  return m;
}
const TABS: { id: Tab; label: string; short?: string; tiny?: string }[] = [
  { id: 'now', label: 'Field now' },
  { id: 'season', label: 'Coming season', tiny: 'Season' },
  { id: 'year', label: 'This field’s year', tiny: 'Year' },
  { id: 'compare', label: 'Compare' },
  { id: 'brief', label: 'Print for your adviser', short: 'Print' },
];

export default function App() {
  const [detail, setDetail] = useDetailState();
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
  const metric = 'cover' as const; // the 3D view shows ground cover; measured water use is on the panel (OpenET)
  const [layersOn, setLayersOn] = useState<Record<string, boolean>>({ hls: true, smap: true, grace: true, imerg: false, modis: false, ecostress: false });
  const [allocation, setAllocation] = useState<Record<string, number>>({});
  const [briefOpen, setBriefOpen] = useState(false);
  const [briefPick, setBriefPick] = useState<string | null>(null);
  const [bcOpen, setBcOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [switchOpen, setSwitchOpen] = useState(false);
  const [dateOpen, setDateOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [timedOut, setTimedOut] = useState<string | null>(null);
  const [strips, setStrips] = useState<Record<string, Record<number, string>>>({});
  useEffect(() => {
    if (!switchOpen && !dateOpen) return;
    const off = (e: MouseEvent) => { const el = e.target as HTMLElement; if (!el.closest('.tb-switch')) setSwitchOpen(false); if (!el.closest('.tb-date-wrap')) setDateOpen(false); };
    document.addEventListener('mousedown', off);
    return () => document.removeEventListener('mousedown', off);
  }, [switchOpen, dateOpen]);
  const [view, setView] = useState({ zoom: 5.75, pitch: 0, bearing: 0, lat: 37.35, lon: -119.9 });

  useEffect(() => {
    api.getLocations().then(({ locations: ls, prov, live: lv }) => { api.getStrips(ls.map((l) => l.id)).then(setStrips); setLocations(ls); setLocProv(prov); setLive(lv); setAllocation(Object.fromEntries(ls.map((l) => [l.id, l.water.allocation_input.value]))); });
    api.getDatasets().then(setDatasets);
    api.getGlossary().then(setGlossary);
    api.getBC().then(setBC);
  }, []);
  const selected = useMemo(() => locations.find((l) => l.id === selectedId) ?? null, [locations, selectedId]);
  useEffect(() => {
    if (!selected || live == null) { setData(null); return; }
    let ok = true;
    setTimedOut(null);
    const to = setTimeout(() => ok && setTimedOut(selected.id), 15000);
    api.getField(selected, live, (b) => ok && setData(b)).then((b) => ok && setData(b));
    api.getDaily(selected.id).then((r) => ok && setDaily({ id: selected.id, ...r }));
    api.getOutlook(selected.id, live).then((o) => ok && setOutlook({ id: selected.id, o }));
    api.getISS(selected).then((v) => ok && setISS({ id: selected.id, v }));
    return () => { ok = false; clearTimeout(to); };
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
  const phone = usePhone();
  const leftInset = phone ? 0 : leftPanel ? Math.min(460, window.innerWidth * 0.46) + 24 : 0;
  const rightInset = layersOpen ? 396 : 0;
  const bottomInset = phone ? 64 + (leftPanel ? 160 : 0) : yearExpanded ? (showEarlier ? 470 : 290) : 12;
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
    <DetailCtx.Provider value={{ on: detail, set: setDetail }}>
    <div className={`app ${detail ? 'detail-on' : 'detail-off'}`}>
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
              {results.length === 0 && <p className="muted pad">No field matches.</p>}
            </div>
          )}
        </div>
        <nav className="tb-tabs" aria-label="Sections">
          {TABS.map((tb) => (
            <button key={tb.id} className={tabOn(tb.id) ? 'on' : ''} onClick={() => onTab(tb.id)} data-testid={`tab-${tb.id}`} disabled={!selected && tb.id !== 'now'} title={selected ? undefined : 'Pick a field first'}><span className="tb-long">{tb.label}</span>{tb.short && <span className="tb-short">{tb.short}</span>}{tb.tiny && <span className="tb-tiny">{tb.tiny}</span>}</button>
          ))}
        </nav>
        <button className={`tb-menu-btn ${menuOpen ? 'on' : ''}`} onClick={() => setMenuOpen(!menuOpen)} aria-label="Menu" aria-expanded={menuOpen} data-testid="menu"><Icon name={menuOpen ? 'close' : 'menu'} size={22} /></button>
        <div className={`tb-right ${menuOpen ? 'open' : ''}`}>
          <div className="tb-date-wrap">
            <button className={`tb-date ${dateOpen ? 'open' : ''}`} onClick={() => setDateOpen(!dateOpen)} data-testid="date-control" aria-expanded={dateOpen}>
              <small>Viewing</small><b>{t === TODAY_T ? `Today, ${tLabel(t).charAt(0).toLowerCase()}${tLabel(t).slice(1)}` : tLabel(t)}</b><Icon name="down" size={16} />
            </button>
            {dateOpen && (
              <div className="tb-datepop" data-testid="date-pop">
                <div className="dp-quick">
                  {QUICK.map((q) => <button key={q.label} className={t === q.t ? 'on' : ''} onClick={() => { setT(q.t); setPlaying(false); setDateOpen(false); }}>{q.label}<small>{q.sub}</small></button>)}
                </div>
                <div className="dp-months">
                  {YEARS.filter((y) => showEarlier || y >= RECENT_FROM).slice().reverse().map((y) => (
                    <div key={y} className="dp-year"><b>{y}</b>
                      {MONTHS.map((m, k) => { const tt = tOf(y, k * 3 + 1), future = tt > TODAY_T; return <button key={m} disabled={future} className={yearOf(t) === y && Math.floor(dekadOf(t) / 3) === k ? 'on' : ''} onClick={() => { setT(tt); setPlaying(false); setDateOpen(false); }}>{m}</button>; })}
                    </div>
                  ))}
                </div>
                <div className="dp-foot">
                  <button className="link" onClick={() => setShowEarlier(!showEarlier)}>{showEarlier ? 'Hide earlier years' : 'Show earlier years (2016–2022)'}</button>
                  {t !== TODAY_T && <button className="link" onClick={() => { setT(TODAY_T); setDateOpen(false); }}>Back to today</button>}
                </div>
              </div>
            )}
          </div>
          <button className={`tb-layers ${layersOpen ? 'on' : ''}`} onClick={() => setLayersOpen(!layersOpen)} data-testid="layers-btn"><Icon name="layers" size={16} />Map layers</button>
        </div>
      </header>
      <nav className="mob-tabs" aria-label="Sections">
        {TABS.map((tb) => <button key={tb.id} className={tabOn(tb.id) ? 'on' : ''} onClick={() => { setMenuOpen(false); onTab(tb.id); }} disabled={!selected && tb.id !== 'now'} data-testid={`mtab-${tb.id}`}>{tb.short ?? MOB[tb.id] ?? tb.label}</button>)}
      </nav>
      {t !== TODAY_T && <div className="date-banner" data-testid="date-banner">Showing {tLabel(t)}<button className="link" onClick={() => { setT(TODAY_T); setPlaying(false); }}>Back to today</button></div>}

      {leftPanel === 'card' && selected && <FieldPanel key={selected.id} loc={selected} prov={prov} cal={d?.cal ?? null} regional={regional} regionalLive={regionalLive} strategies={d?.strategies ?? null} allocation={allocation[selected.id]} exampleLimit={exampleLimit} daily={dl?.daily ?? null}
        nasa={d?.nasa ?? null} nasaNow={d?.nasaNow ?? null} extras={d?.extras ?? { openet: null, stress: null, insurance: null, water: null }} iss={issNow} dataState={d ? 'ready' : timedOut === selected.id ? 'timeout' : 'loading'} dailyState={dl?.daily ? 'ready' : dl || timedOut === selected.id ? 'timeout' : 'loading'}
        t={t} setT={setT} events={events} onStep={onStep} onClose={() => setCardOpen(false)} />}
      {leftPanel === 'fields' && <FieldPicker locations={locations} live={live} strips={strips} selectedId={selectedId} onSelect={select} onBC={goBC} onClose={panel === 'fields' ? () => setPanel('none') : undefined} />}
      {selected && !leftPanel && !yearExpanded && panel === 'none' && <button className="reopen pill glass" onClick={() => setCardOpen(true)}><Icon name="info" size={16} />{fieldName(selected)}</button>}

      {panel === 'season' && selected && d && <ComingSeason nasaNow={d.nasaNow} regional={regional} regionalLive={regionalLive} loc={selected} outlook={ol} cal={d.cal} daily={dl?.daily ?? null} strategies={d.strategies} allocation={allocation[selected.id]} exampleLimit={exampleLimit} prov={prov} onCompare={() => setPanel('compare')} onClose={() => setPanel('none')} />}
      {panel === 'compare' && selected && d && <ComparePanel loc={selected} strategies={d.strategies} daily={dl?.daily ?? null} allocation={allocation[selected.id]} exampleLimit={exampleLimit} live={!!live} cal={d.cal} setAllocation={(v) => setAllocation({ ...allocation, [selected.id]: v })}
        onBrief={(id) => { setBriefPick(id); setBriefOpen(true); }} onClose={() => setPanel('none')} />}

      {layersOpen && <LayersDrawer datasets={datasets} on={layersOn} toggle={(id) => setLayersOn({ ...layersOn, [id]: !layersOn[id] })} loc={selected}  onClose={() => setLayersOpen(false)} />}

      {drilled && panel !== 'compare' && panel !== 'season' && (
        <div className="hud glass" data-testid="hud">
          <span className="hud-title"><Icon name="cube" size={16} />Under the field</span>

          <div className="hud-legend">
            {(['b', 'p', 'c', 'w'] as CoverClass[]).map((c) => <span key={c}><i style={{ background: CLASS_COLOR[c] }} />{({ b: 'Bare', p: 'Thin', c: 'Crop', w: 'Flooded' } as Record<string, string>)[c]}</span>)}
            <span className="hud-note">taller = greener</span>
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

      {yearExpanded && selected && d?.cal && (
        <div className="year-dock" data-testid="year-dock">
          <YearSheet t={t} setT={setT} loc={selected} cal={d.cal} daily={dl?.daily ?? null} ml={d.ml} extras={d.extras} calSource={calSource(d.prov.calendar)} events={events}
            playing={playing} setPlaying={setPlaying} showEarlier={showEarlier} setShowEarlier={setShowEarlier} setExpanded={(b) => setYearOpen(b)} />
        </div>
      )}

      {briefOpen && selected && d && <RotationBrief loc={selected} strategies={d.strategies} pick={briefPick} setPick={setBriefPick} allocation={allocation[selected.id]} exampleLimit={exampleLimit} prov={prov} outlook={ol} nasaNow={d.nasaNow} cal={d.cal} daily={dl?.daily ?? null} onClose={() => setBriefOpen(false)} />}
    </div>
    </DetailCtx.Provider>
  );
}
