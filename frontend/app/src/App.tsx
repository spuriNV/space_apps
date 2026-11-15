import { getCatalog, type Catalog } from './components/week/catalog';
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
import { FieldTimeline, type SimMode } from './components/ui/FieldTimeline';
import RotationBrief from './components/brief/RotationBrief';
import BriefStep from './components/brief/BriefStep';
import { RainTimeline, WeatherControl, droughtRegion, type RainMode, type WxLayer } from './components/rain/RainControl';
import { BCCard, LayersDrawer } from './components/Panels';
import { LandPanel } from './components/lands/LandPanel';
import type { LandFeature } from './components/lands/lands';
import { FieldPanel, FieldPicker } from './components/ui/Options';
import { setGlossary } from './components/ui/What';
import { DrawLayer, type DrawHostHandle } from './components/draw/DrawLayer';
import { DRAFT_ID, parseFieldHash, useMyFields } from './myFields';
import { focusNationTools } from './components/week/NationTools';
import { DetailCtx, useDetailState } from './components/ui/Detail';
import { FLOW, ProvList, acres, fieldName, place, type FlowId, type Step } from './components/ui/shared';
import { announce, onOtherOpen } from './overlays';
import { MenuItems } from './components/a11y/MenuItems';
import { AccessibilityPage } from './components/a11y/AccessibilityPage';
import { MapList, type ReserveRow } from './components/a11y/MapList';
import { usePrefs } from './components/a11y/prefs';
import AskChat from './components/chat/AskChat';
import Tour, { tourDismissed, TOUR_STOPS } from './components/ui/Tour';

// One look (Extension bulletin, tokens at the top of styles.css). Four screens: pick a field, your field now, coming season, compare and print.
type Panel = 'none' | 'fields' | 'season' | 'compare';
/** Quick dates in the grower's words for the "Viewing" control. */
const QUICK: { label: string; sub: string; t: number }[] = [
  { label: 'Today', sub: 'mid Nov 2026', t: TODAY_T },
  { label: 'Last summer', sub: 'Jul 2026', t: tOf(2026, 19) },
  { label: 'Last spring', sub: 'Apr 2026', t: tOf(2026, 10) },
  { label: '2023 floods', sub: 'Mar 2023', t: tOf(2023, 7) },
  { label: '2022 drought', sub: 'Jul 2022', t: tOf(2022, 19) },
];
/** Phone width: the field panel becomes a bottom sheet and the sections a bottom tab bar. */
function usePhone() {
  const q = '(max-width: 640px)';
  const [m, setM] = useState(() => typeof window !== 'undefined' && window.matchMedia(q).matches);
  useEffect(() => { const mq = window.matchMedia(q); const f = () => setM(mq.matches); mq.addEventListener('change', f); return () => mq.removeEventListener('change', f); }, []);
  return m;
}

const noop = () => {};

export default function App() {
  const [detail, setDetail] = useDetailState();
  const map = useRef<MapHandle>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const [plainLocations, setLocations] = useState<Location[]>([]);
  const [drawing, setDrawing] = useState<{ hideId: string | null } | null>(null); // a drawing session is open (taps and picks are off)
  useEffect(() => onOtherOpen('layers', () => setLayersOpen(false)), []);
  const [listOpen, setListOpen] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);
  useEffect(() => { const f = () => setAboutOpen(true); window.addEventListener('croplytics:about', f); return () => window.removeEventListener('croplytics:about', f); }, []);
  const draw = useRef<DrawHostHandle>(null);
  const [locProv, setLocProv] = useState<Record<string, api.ProvMap>>({});
  const [live, setLive] = useState<boolean | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [bc, setBC] = useState<BCInfo | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  // fields the user drew join the list: pins, outlines, switcher and the panel treat them like any other field
  const mf = useMyFields(selectedId);
  const locations = useMemo(() => [...plainLocations, ...mf.locs], [plainLocations, mf.locs]);
  const [data, setData] = useState<api.FieldBundle | null>(null);
  const [t, setT] = useState(TODAY_T);
  const [showEarlier, setShowEarlier] = useState(false);
  const [daily, setDaily] = useState<{ id: string; daily: Daily | null; prov: api.Prov } | null>(null);
  const [outlook, setOutlook] = useState<{ id: string; o: api.Outlook } | null>(null);
  const [iss, setISS] = useState<{ id: string; v: Awaited<ReturnType<typeof api.getISS>> } | null>(null);
  const [playing, setPlaying] = useState(false);
  const [replaying, setReplaying] = useState(false);
  const [sim, setSim] = useState<SimMode>(null); // Compare's "run a year on the map": a one-year playback with a water banner
  const [panel, setPanel] = useState<Panel>('none');
  const [cardOpen, setCardOpen] = useState(true);
  const [layersOpen, setLayersOpen] = useState(false);
  const [yearOpen, setYearOpen] = useState(false);
  const detector = 'rule' as const;
  const metric = 'cover' as const; // the 3D view shows ground cover; measured water use is on the panel (OpenET)
  const [layersOn, setLayersOn] = useState<Record<string, boolean>>({ hls: true, smap: true, grace: true, imerg: false, modis: false, ecostress: false, reserves: true, lands: true });
  // First Nations lands: every BC reserve and California tribal land, on the whole map; a click opens the Nation panel
  const [lands, setLands] = useState<LandFeature[] | null>(null);
  const [landId, setLandId] = useState<string | null>(null);
  useEffect(() => { api.getLands().then(setLands); }, []);
  const land = useMemo(() => lands?.find((f) => f.properties.id === landId) ?? null, [lands, landId]);
  const [reserves, setReserves] = useState<{ id: string; fc: GeoJSON.FeatureCollection | null } | null>(null);
  const [allocation, setAllocation] = useState<Record<string, number>>({});
  const [briefOpen, setBriefOpen] = useState(false);
  const [briefPreview, setBriefPreview] = useState(false);
  // rain and drought on the map (Windy-style layer card; NOAA WPC rain forecast and U.S. Drought Monitor via app/rain)
  const [wxOn, setWxOn] = useState(false);
  const [wxLayer, setWxLayer] = useState<WxLayer>('rain');
  const [rainMode, setRainMode] = useState<RainMode>('total');
  const [rainDays, setRainDays] = useState<api.RainDays>(7);
  const [rain, setRain] = useState<{ days: api.RainDays; data: api.RainForecast | null } | null>(null);
  const [steps, setSteps] = useState<(api.RainForecast | null)[]>(() => Array(12).fill(null));
  const [stepsDone, setStepsDone] = useState(0);
  const [rainStep, setRainStep] = useState(0);
  const [rainPlaying, setRainPlaying] = useState(false);
  const [drought, setDrought] = useState<api.DroughtNow | null | undefined>(undefined);
  const rainTotal = wxOn && wxLayer === 'rain' && rainMode === 'total';
  const rainHourly = wxOn && wxLayer === 'rain' && rainMode === 'hourly';
  useEffect(() => {
    if (!rainTotal) return;
    let ok = true;
    api.getRainForecast(rainDays).then((r) => ok && setRain({ days: rainDays, data: r }));
    return () => { ok = false; };
  }, [rainTotal, rainDays]);
  useEffect(() => { // the timeline: all twelve 6-hour steps, so play never waits
    if (!rainHourly || stepsDone === 12) return;
    let ok = true;
    Array.from({ length: 12 }, (_, k) => api.getRainStep(k).then((r) => { if (!ok) return; setSteps((xs) => { const n = [...xs]; n[k] = r; return n; }); setStepsDone((c) => c + 1); }));
    return () => { ok = false; };
  }, [rainHourly]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!rainPlaying || !rainHourly) return;
    const h = setInterval(() => setRainStep((k) => (k + 1) % 12), 1100);
    return () => clearInterval(h);
  }, [rainPlaying, rainHourly]);
  useEffect(() => { if (!rainHourly) setRainPlaying(false); }, [rainHourly]);
  useEffect(() => { if (wxOn && wxLayer === 'drought' && drought === undefined) api.getDroughtNow().then(setDrought); }, [wxOn, wxLayer, drought]);
  const rainNow = rainTotal ? (rain?.days === rainDays ? rain.data : null) : rainHourly ? steps[rainStep] : null;
  const [view, setView] = useState({ zoom: 5.75, pitch: 0, bearing: 0, lat: 37.35, lon: -119.9 });
  const dRegion = droughtRegion(view.lat, view.lon);
  const droughtNow = wxOn && wxLayer === 'drought' && dRegion === 'na' ? drought ?? null : null;
  const rainState: 'idle' | 'loading' | 'ready' | 'error' = !wxOn ? 'idle'
    : wxLayer === 'drought' ? (drought === undefined ? 'loading' : drought ? 'ready' : 'error')
    : rainTotal ? (rain?.days !== rainDays ? 'loading' : rain.data ? 'ready' : 'error')
    : steps[rainStep] ? 'ready' : stepsDone === 12 ? 'error' : 'loading';
  const [briefPick, setBriefPick] = useState<string | null>(null);
  const [bcOpen, setBcOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [switchOpen, setSwitchOpen] = useState(false);
  const [dateOpen, setDateOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [timedOut, setTimedOut] = useState<string | null>(null);
  const [strips, setStrips] = useState<Record<string, Record<number, string>>>({});
  const [sheetPx, setSheetPx] = useState(() => (typeof window !== 'undefined' ? Math.round(window.innerHeight * 0.35) : 300)); // phone: visible sheet height
  useEffect(() => {
    if (!switchOpen && !dateOpen) return;
    const off = (e: MouseEvent) => { const el = e.target as HTMLElement; if (!el.closest('.tb-switch')) setSwitchOpen(false); if (!el.closest('.tb-date-wrap')) setDateOpen(false); };
    document.addEventListener('mousedown', off);
    return () => document.removeEventListener('mousedown', off);
  }, [switchOpen, dateOpen]);

  useEffect(() => {
    api.getLocations().then(({ locations: ls, prov, live: lv }) => { api.getStrips(ls.map((l) => l.id)).then(setStrips); setLocations(ls); setLocProv(prov); setLive(lv); setAllocation(Object.fromEntries(ls.map((l) => [l.id, l.water.allocation_input.value]))); });
    api.getDatasets().then(setDatasets);
    api.getGlossary().then(setGlossary);
    api.getBC().then(setBC);
  }, []);
  useEffect(() => setAllocation((a) => (mf.locs.every((l) => l.id in a) ? a : { ...a, ...Object.fromEntries(mf.locs.filter((l) => !(l.id in a)).map((l) => [l.id, l.water.allocation_input.value])) })), [mf.locs]);
  const selected = useMemo(() => locations.find((l) => l.id === selectedId) ?? null, [locations, selectedId]);
  // a real BC field replaces the old "Why not BC yet" row, pins and card
  const hasBC = locations.some(api.isBC);
  // reserve outlines near a BC field: context only, fetched when the layer is first switched on
  const reservesAvail = !layersOn.lands && !!selected && !selected.mine && (api.isBC(selected) || api.isSpot(selected.id));
  const wantReserves = reservesAvail && !!layersOn.reserves;
  useEffect(() => {
    if (!wantReserves || !selected || reserves?.id === selected.id) return;
    let ok = true;
    api.getReserves(selected.id).then((fc) => ok && setReserves({ id: selected.id, fc }));
    return () => { ok = false; };
  }, [wantReserves, selected, reserves?.id]);
  const reservesFc = wantReserves && reserves?.id === selected?.id ? reserves.fc : null;
  // reserves arrived: fit the field and its nearest reserves in one view
  const fitDone = useRef('');
  useEffect(() => {
    if (!reservesFc?.features.length || !selected || fitDone.current === selected.id || yearOpen) return;
    fitDone.current = selected.id;
    const h = setTimeout(() => map.current?.fitReserves(selected, reservesFc), 700);
    return () => clearTimeout(h);
  }, [reservesFc, selected, yearOpen]);
  useEffect(() => {
    if (!selected || live == null) { setData(null); return; }
    const spot = api.isLite(selected.id);
    let ok = true;
    setTimedOut(null);
    const to = setTimeout(() => ok && setTimedOut(selected.id), 15000);
    const caPresets = locations.filter((l) => !api.isLite(l.id) && l.region !== 'bc');
    // 3D stack paints at once (shifted nearest grid for pt_/my_, bundled squares for prepared fields). APIs upgrade it.
    setData(api.fieldStackSeed(selected, live, caPresets));
    api.prefetchFieldStack(selected, caPresets);
    api.getField(selected, live, (b) => ok && setData(b), caPresets).then((b) => ok && setData(b));
    api.getDaily(selected.id).then((r) => ok && setDaily({ id: selected.id, ...r }));
    // always resolve outlook (presets load the file; tapped/drawn fields get a quiet "not built yet" so Coming season never spins)
    api.getOutlook(selected.id, live).then((o) => ok && setOutlook({ id: selected.id, o }));
    if (!spot) api.getISS(selected).then((v) => ok && setISS({ id: selected.id, v }));
    return () => { ok = false; clearTimeout(to); };
  }, [selected, live, locations]);
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
    if (sim) {
      const end = tOf(sim.year, 35);
      const h = setInterval(() => setT((v) => { if (v >= end) { setPlaying(false); return end; } return v + 1; }), 160);
      return () => clearInterval(h);
    }
    const h = setInterval(() => setT((v) => (v >= T_MAX ? tStart(showEarlier) : Math.max(v + 1, tStart(showEarlier)))), 220);
    return () => clearInterval(h);
  }, [playing, showEarlier, sim]);
  const stopSim = useCallback(() => { setPlaying(false); setSim(null); setT(TODAY_T); }, []);
  const runSim = useCallback((next: NonNullable<SimMode>, startT: number) => { setSim(next); setT(startT); setPlaying(true); }, []);

  const d = data && data.id === selectedId ? data : null;
  // ?replay=1: open the year view and start the replay once the field's grid has loaded
  const replayLink = useRef(new URLSearchParams(location.search).get('replay') === '1');
  useEffect(() => {
    if (!replayLink.current || !selectedId || !d?.cells?.layers || !d.cal) return;
    replayLink.current = false;
    setYearOpen(true); setPanel('none'); setBriefOpen(false);
    setTimeout(() => map.current?.replay(locations.find((l) => l.id === selectedId)!), 600);
  }, [selectedId, d]);
  // the grower's current rotation: the satellite-detected one unless they changed it (step 2), remembered per field
  const [todayPick, setTodayPick] = useState<Record<string, string>>(api.loadTodayPicks);
  const pickToday = (fid: string, sid: string | null) => setTodayPick((m) => { const n = { ...m }; if (sid) n[fid] = sid; else delete n[fid]; api.saveTodayPicks(n); return n; });
  const strats = useMemo(() => (d ? api.withToday(d.strategies, todayPick[d.id]) : null), [d, todayPick]);
  useEffect(() => { (window as unknown as Record<string, unknown>).__app = { setT, select: (id: string) => select(id), ready: !!d }; });
  const dl = daily && daily.id === selectedId ? daily : null;
  const ol = outlook && outlook.id === selectedId ? outlook.o : null;
  const issNow = iss && iss.id === selectedId ? iss.v : null;
  const regional = d?.regional ?? null;
  const regionalLive: api.RegionalLive = d?.regionalLive ?? { smap: false, grace: false, soilSource: null };
  const exampleLimit = !!selected && allocation[selected.id] === api.EXAMPLE_LIMIT[selected.id];
  const prov: api.ProvMap = { ...(selected ? locProv[selected.id] ?? mf.prov[selected.id] : {}), ...(d?.prov ?? {}), ...(dl ? { daily: dl.prov } : {}), ...(ol ? { outlook_cpc: ol.prov.cpc, outlook_water: ol.prov.water, outlook_alloc: ol.prov.alloc } : {}) };

  const select = useCallback((id: string) => {
    setSim(null);
    const loc = locations.find((l) => l.id === id);
    if (!loc) return;
    if (!api.isSpot(id)) dropSpot();
    setSelectedId(id); setCardOpen(true); setBcOpen(false); setLandId(null);
    setPanel('none'); setYearOpen(false);
    if (loc.mine) map.current?.fitField(loc); else map.current?.flyToField(loc, 'card');
  }, [locations]);

  // ---------- tap anywhere: a pin, the panel in its loading state at once, then GET /api/analyze fills it ----------
  const tapSeq = useRef(0);
  const locsRef = useRef(locations);
  locsRef.current = locations;
  /** forget the tapped spot (another field picked, or back to California) and its #spot= link */
  const dropSpot = () => {
    tapSeq.current++;
    setLocations((ls) => (ls.some((l) => api.isSpot(l.id)) ? ls.filter((l) => !api.isSpot(l.id)) : ls));
    if (location.hash.startsWith('#spot=')) history.replaceState(null, '', location.pathname + location.search);
  };
  const [pickTab, setPickTab] = useState<'fields' | 'lands'>('fields');
  const openLand = useCallback((id: string) => {
    const f = lands?.find((x) => x.properties.id === id);
    if (!f) return;
    setSim(null); dropSpot();
    setLandId(id); setSelectedId(null); setPanel('none'); setYearOpen(false); setBriefOpen(false); setBcOpen(false);
    setTimeout(() => map.current?.flyToLand(f), 60); // after the panel is in, so the map fits the land beside it
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lands]);
  const tapSpot = useCallback(async (lat0: number, lon0: number) => {
    const lat = Math.round(lat0 * 1e4) / 1e4, lon = Math.round(lon0 * 1e4) / 1e4;
    const seq = ++tapSeq.current;
    const ph = api.spotPlaceholder(lat, lon);
    const caPresets = locsRef.current.filter((l) => !api.isLite(l.id) && l.region !== 'bc');
    api.prefetchFieldStack(ph, caPresets);
    setLocations((ls) => [...ls.filter((l) => !api.isSpot(l.id)), ph]);
    setSelectedId(ph.id); setCardOpen(true); setBcOpen(false); setYearOpen(false); setBriefOpen(false); setLandId(null);
    setPanel((p) => (p === 'season' || p === 'compare' ? p : 'none'));
    history.replaceState(null, '', `#spot=${ph.id}`);
    map.current?.focusSpot(lat, lon);
    const r = await api.analyzeSpot(lat, lon);
    if (seq !== tapSeq.current) return; // another tap, or the spot was closed, while this one ran
    if (r.kind === 'preset') {
      // the tap fell inside one of the prepared fields: open that field instead
      const pre = locsRef.current.find((l) => l.id === r.id);
      dropSpot();
      if (pre) { setSelectedId(pre.id); map.current?.flyToField(pre, 'card'); } else setSelectedId(null);
      return;
    }
    if (r.kind === 'error') {
      setLocations((ls) => ls.map((l) => (l.id === ph.id ? { ...l, spot: { ...l.spot!, state: 'error', error: r.message } } : l)));
      return;
    }
    const loc = r.loc;
    setLocProv((p) => ({ ...p, [loc.id]: r.prov }));
    setAllocation((a) => ({ ...a, [loc.id]: loc.water.allocation_input.value }));
    setLocations((ls) => [...ls.filter((l) => !api.isSpot(l.id)), loc]);
    if (loc.id !== ph.id) { setSelectedId(loc.id); history.replaceState(null, '', `#spot=${loc.id}`); }
  }, []);
  // farm catalog pins and list (components/week): a pick opens the point panel for that farm
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [catGroup, setCatGroup] = useState<string | null>(null);
  useEffect(() => { getCatalog().then(setCatalog); }, []);
  const pickCatalog = useCallback((it: { lat: number; lon: number }) => { tapSpot(it.lat, it.lon); }, [tapSpot]);
  // a shared link (#spot=pt_...) opens that spot once the field list is in
  const hashDone = useRef(false);
  useEffect(() => {
    if (hashDone.current || live == null) return;
    hashDone.current = true;
    const m = /^#spot=(pt_[nsew\d_]+)$/.exec(location.hash);
    const pt = m ? api.spotPoint(m[1]) : null;
    if (pt) tapSpot(pt.lat, pt.lon);
  }, [live, tapSpot]);

  // ---------- my fields: a drawing session, saving (the panel shows at once in its skeleton state), the #field= link ----------
  const onSubmitting = () => {
    dropSpot();
    setSelectedId(DRAFT_ID);
    setCardOpen(true); setPanel('none'); setYearOpen(false); setBriefOpen(false); setBcOpen(false);
    setTimeout(() => {
      const l = locsRef.current.find((x) => x.id === DRAFT_ID);
      if (l) {
        const caPresets = locsRef.current.filter((x) => !api.isLite(x.id) && x.region !== 'bc');
        api.prefetchFieldStack(l, caPresets);
        map.current?.fitField(l);
      }
    }, 80);
  };
  const onSaved = (id: string | null) => { if (id) { setSelectedId((cur) => (cur === DRAFT_ID ? id : cur)); setTimeout(() => { const l = locsRef.current.find((x) => x.id === id); if (l && locsRef.current.length) map.current?.fitField(l); }, 80); } };
  const openMine = (id: string) => { setSelectedId(id); setCardOpen(true); setPanel('none'); setTimeout(() => { const l = locsRef.current.find((x) => x.id === id); if (l) map.current?.fitField(l); }, 120); };
  useEffect(() => { if (!selectedId && mf.draft?.error) mf.dropDraft(); else if (mf.draft?.error && selectedId !== DRAFT_ID) mf.dropDraft(); }, [selectedId, mf.draft]);
  const hashInit = useRef(false);
  useEffect(() => {
    if (!hashInit.current) { hashInit.current = true; if (parseFieldHash()) return; }
    const mine = api.isMine(selectedId) && selectedId !== DRAFT_ID;
    if (mine) history.replaceState(null, '', `${location.pathname}${location.search}#field=${selectedId}`);
    else if (location.hash.startsWith('#field=') && !mf.shared) history.replaceState(null, '', location.pathname + location.search);
  }, [selectedId, mf.shared]);

  const openPanel = (id: Panel) => {
    if (id !== 'fields' && !selected) { setPanel('fields'); return; }
    if (id === 'none') { setPanel('none'); setCardOpen(true); setYearOpen(false); return; }
    setPanel((p) => (p === id ? 'none' : id));
    setYearOpen(false);
  };
  // First Nations example: pick the Salmon River field, open step 2 and bring the Nation tools into view
  const NATION_ID = 'bc_salmon_river_forage';
  const openNationsExample = () => {
    if (!locations.some((l) => l.id === NATION_ID)) return;
    setDetail(true); select(NATION_ID); setLayersOn((l) => ({ ...l, reserves: true }));
    setTimeout(() => focusNationTools(), 300);
  };
  const nationsHash = useRef(location.hash === '#nations');
  useEffect(() => {
    if (!nationsHash.current || !locations.some((l) => l.id === NATION_ID)) return;
    nationsHash.current = false;
    openNationsExample();
  });
  // Example field (#example): Colusa rice, then a short skippable tour
  const EX_ID = 'car_colusa_rice';
  const [tour, setTour] = useState<number | null>(null);
  const openExample = (force = false) => {
    if (!locations.some((l) => l.id === EX_ID)) return;
    setSwitchOpen(false); setMenuOpen(false); setBriefOpen(false);
    select(EX_ID);
    if (force || !tourDismissed()) setTour(0); else setTour(null);
  };
  const exHash = useRef(location.hash === '#example');
  useEffect(() => {
    if (!exHash.current || !locations.some((l) => l.id === EX_ID)) return;
    exHash.current = false;
    openExample();
  });
  const tourGo = (i: number) => {
    if (replaying) map.current?.cancelReplay();
    const id = TOUR_STOPS[i].step;
    setSwitchOpen(false); setMenuOpen(false);
    if (id === 'now') { setBriefOpen(false); setPanel('none'); setCardOpen(true); setYearOpen(false); }
    else if (id === 'compare') { setBriefOpen(false); setYearOpen(false); setPanel('compare'); }
    else { setBriefOpen(true); setBriefPreview(false); setYearOpen(false); }
    setTour(i);
  };
  const goHome = () => { setLandId(null); setSim(null); setPlaying(false); dropSpot(); setSelectedId(null); setPanel('none'); setYearOpen(false); setBcOpen(false); setBriefOpen(false); map.current?.flyHome(); };
  const goBC = () => { setBcOpen(true); setPanel('none'); setYearOpen(false); map.current?.flyTo(49.9, -121.0, 6.4); };
  const onStep = (s: Step) => {
    if (!selected) return;
    if (s === 'drill') { setPanel('none'); map.current?.flyToField(selected, 'drill'); }
    else if (s === 'year') { setPanel('none'); setBriefOpen(false); setYearOpen(true); map.current?.flyToField(selected, 'year'); }
    else if (s === 'compare') openPanel('compare');
    else if (s === 'season') openPanel('season');
    else { setBriefPick(null); setBriefOpen(true); }
  };

  const reserveRows = useMemo<ReserveRow[]>(() => (reservesFc?.features ?? []).map((f) => {
    const pr = (f.properties ?? {}) as { name?: string; distance_to_field_km?: number };
    const xs: number[] = [], ys: number[] = [];
    const walk = (c: unknown): void => { if (Array.isArray(c) && typeof c[0] === 'number') { xs.push(c[0]); ys.push(c[1] as number); } else if (Array.isArray(c)) c.forEach(walk); };
    walk((f.geometry as GeoJSON.Polygon).coordinates);
    return { name: pr.name ?? 'Reserve', km: pr.distance_to_field_km, lon: (Math.min(...xs) + Math.max(...xs)) / 2, lat: (Math.min(...ys) + Math.max(...ys)) / 2 };
  }), [reservesFc]);
  // "Pause all motion": stop the replay and any playing timeline
  const pausedMotion = usePrefs().pause;
  useEffect(() => { if (pausedMotion) { map.current?.cancelReplay(); setPlaying(false); } }, [pausedMotion]);

  const yearExpanded = yearOpen && !!selected && panel !== 'compare' && panel !== 'season';
  // left column: a tool panel, else the field panel, else (nothing picked yet) the "Pick your field" list
  const toolPanel = panel === 'fields' ? panel : null;
  const leftPanel = yearExpanded || drawing ? null : land ? 'land' : toolPanel ?? (panel === 'none' && selected && cardOpen && !briefOpen ? 'card' : panel === 'none' && !selected && !bcOpen ? 'fields' : null);
  const phone = usePhone();
  // steps 3 to 5 sit in the same left slot as step 2 (one frame for the whole flow)
  const stepPanel = !!selected && !!d && !yearExpanded && !drawing && (briefOpen || panel === 'season' || panel === 'compare');
  const leftInset = phone ? 0 : leftPanel || stepPanel ? Math.min(460, window.innerWidth * 0.46) + 24 : 0;
  const rightInset = layersOpen ? 396 : 0;
  const bottomInset = phone ? 64 + (leftPanel || stepPanel ? sheetPx : 0) : yearExpanded ? (showEarlier ? 470 : 290) : 12;
  // "Ten years from orbit": needs the real quarterly grid (preset fields); the button is hidden elsewhere
  const canReplay = !!selected && !!d?.cells?.layers && d.cells.layers.filter((l) => l.kind === 'quarter_median').length >= 8 && layersOn.hls;
  const startReplay = () => {
    if (!selected) return;
    if (replaying) { map.current?.cancelReplay(); return; }
    setPlaying(false); setYearOpen(true);
    map.current?.replay(selected);
  };
  const stackField = !!selected && !!d?.cells && !!d.cal;
  const drilled = stackField && view.zoom > 13.05;
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
      ...locations.filter((l) => !api.isSpot(l.id)).map((l) => ({ key: l.id, title: fieldName(l), sub: `${place(l)} · ${acres(l)} acres${l.dwr_id ? ' · state field no. ' + l.dwr_id : ''}`, icon: 'fields', go: () => select(l.id) })),
      ...(hasBC ? [] : [{ key: 'bc', title: 'Sumas Prairie, British Columbia', sub: 'Not set up yet: why', icon: 'info', go: goBC }]),
      { key: 'ca', title: 'California', sub: 'Back to the whole state', icon: 'home', go: goHome },
    ];
    return q ? items.filter((i) => (i.title + i.sub).toLowerCase().includes(q)) : items;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, locations, select]);

  // the numbered flow: step 1 is the picker (or nothing picked), 2 the field card (and its year view), 3 to 5 their panels
  const step: FlowId = !selected || panel === 'fields' ? 'pick' : briefOpen ? 'brief' : panel === 'compare' ? 'compare' : panel === 'season' ? 'season' : 'now';
  const goStep = (id: FlowId) => {
    setSwitchOpen(false); setMenuOpen(false);
    if (id === 'pick' || !selected) { setLandId(null); setBriefOpen(false); setYearOpen(false); setPanel('fields'); return; }
    setBriefOpen(id === 'brief'); setBriefPreview(false); setYearOpen(false);
    if (id === 'brief') { if (panel === 'fields') setPanel('none'); return; }
    if (id === 'now') { setPanel('none'); setCardOpen(true); return; }
    setPanel(id);
  };

  return (
    <DetailCtx.Provider value={{ on: detail, set: setDetail }}>
    <div className={`app ${detail ? 'detail-on' : 'detail-off'} ${wxOn ? 'wx-open' : ''}`}>
      <a className="skip-link" href="#field-panel" onClick={(e) => { e.preventDefault(); const el = document.getElementById('field-panel'); if (el) { el.focus(); el.scrollIntoView({ block: 'nearest' }); } else document.getElementById('main')?.focus(); }}>Skip to field panel</a>
      <div className="sr-only" role="status" aria-live="polite" data-testid="live">{selected ? (d ? `${fieldName(selected)} is ready.` : `Loading ${fieldName(selected)}.`) : ''}</div>
      <main id="main" tabIndex={-1} aria-label="Map" className="map-main">
      <MapView ref={map} lands={lands} landsOn={!!layersOn.lands} activeLandId={land ? landId : null} onLandClick={drawing ? undefined : openLand} onToggleLands={() => setLayersOn((l) => ({ ...l, lands: !l.lands }))} locations={drawing?.hideId ? locations.filter((l) => l.id !== drawing.hideId) : locations} bc={hasBC ? null : bc} reserves={reservesFc} reservesChip={reservesAvail} reservesOn={!!layersOn.reserves} onToggleReserves={() => setLayersOn((l) => ({ ...l, reserves: !l.reserves }))} datasets={datasets} selected={selected} cells={d?.cells ?? null} cal={d?.cal ?? null} regional={regional}
        t={t} detector={detector} metric={metric} regionalLive={regionalLive} layersOn={{ ...layersOn, rain: wxOn && wxLayer === 'past' }} leftInset={leftInset} rightInset={rightInset} bottomInset={bottomInset}
        onSelect={drawing ? noop : select} onBC={drawing ? noop : goBC} onReplayT={setT} onReplayRunning={setReplaying} onView={setView} onTap={drawing ? undefined : tapSpot} catalog={catalog?.items ?? null} catGroup={catGroup} onCatalogPick={pickCatalog} rain={rainNow} drought={droughtNow} droughtRegion={wxOn && wxLayer === 'drought' ? dRegion : null} />
      </main>

      <header className="topbar" data-testid="topbar">
        <button className="tb-brand" onClick={goHome} title="Back to all of California">CropLytics</button>
        <div className={`tb-switch ${switchOpen ? 'open' : ''}`}>
          <button className="tb-field" onClick={() => { setSwitchOpen(!switchOpen); setTimeout(() => searchRef.current?.focus(), 0); }} data-testid="field-switch" aria-expanded={switchOpen}>
            <span><small>{selected ? (selected.spot?.state === 'loading' ? (selected.mine ? 'Analysing your field…' : 'Analysing this spot…') : `${place(selected)}, ${acres(selected)} acres`) : 'No field picked'}</small><b>{selected ? fieldName(selected) : 'Pick your field'}</b></span>
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
              <button onClick={() => openExample(true)} data-testid="menu-tour"><b>Take the tour</b><small>A 4-stop walk through the Colusa rice example</small></button>
              {results.length === 0 && <p className="muted pad">No field matches.</p>}
            </div>
          )}
        </div>
        <nav className="tb-tabs" aria-label="Steps" data-testid="steps">
          {FLOW.map((f) => {
            const locked = f.id !== 'pick' && !selected;
            return (
              <button key={f.id} className={step === f.id ? 'on' : ''} aria-current={step === f.id ? 'step' : undefined} onClick={() => goStep(f.id)} data-testid={`tab-${f.id}`} disabled={locked} title={locked ? 'Pick a field first' : f.does} aria-label={`Step ${f.n}: ${f.label}`}>
                <i>{f.n}</i><span className="tb-long">{f.label}</span><span className="tb-short">{f.short}</span>
              </button>
            );
          })}
        </nav>
        <AskChat fieldId={selected && selected.id !== DRAFT_ID && selected.spot?.state !== 'loading' ? selected.id : null} fieldName={selected ? fieldName(selected) : null}
          screen={!selected ? 'pick a field' : briefOpen ? 'print for your adviser' : panel === 'compare' ? 'compare' : panel === 'season' ? 'coming season' : yearExpanded ? "this field's year" : 'field now'}
          date={t === TODAY_T ? `Today, ${tLabel(t)}` : tLabel(t)} waterLimit={selected ? allocation[selected.id] : null} />
        <button className={`tb-menu-btn ${menuOpen ? 'on' : ''}`} onClick={() => setMenuOpen(!menuOpen)} aria-label="Menu" aria-expanded={menuOpen} aria-haspopup="true" data-testid="menu"><Icon name={menuOpen ? 'close' : 'menu'} size={22} /></button>
        <div className={`tb-right ${menuOpen ? 'open' : ''}`}>
          <button className="btn btn-text btn-sm tb-tour" onClick={() => openExample(true)} data-testid="take-tour">Take the tour</button>
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
                  <button className="btn btn-text btn-sm" onClick={() => setShowEarlier(!showEarlier)}>{showEarlier ? 'Hide earlier years' : 'Show earlier years (2016–2022)'}</button>
                  {t !== TODAY_T && <button className="btn btn-outline btn-sm" onClick={() => { setT(TODAY_T); setDateOpen(false); }}>Back to today</button>}
                </div>
              </div>
            )}
          </div>
          <button className={`tb-layers ${layersOpen ? 'on' : ''}`} onClick={() => { if (!layersOpen) announce('layers'); setLayersOpen(!layersOpen); }} data-testid="layers-btn" aria-expanded={layersOpen}><Icon name="layers" size={16} />Map layers</button>
          {menuOpen && <MenuItems onList={() => { announce('draw'); setListOpen(true); }} onAbout={() => setAboutOpen(true)} onDone={() => setMenuOpen(false)} />}
        </div>
      </header>
      {tour != null && selected?.id === EX_ID && <Tour idx={tour} go={tourGo} canReplay={canReplay} onReplay={startReplay} onClose={() => setTour(null)} />}
      <nav className="mob-tabs" aria-label="Steps">
        {FLOW.map((f) => <button key={f.id} className={step === f.id ? 'on' : ''} aria-current={step === f.id ? 'step' : undefined} onClick={() => goStep(f.id)} disabled={f.id !== 'pick' && !selected} data-testid={`mtab-${f.id}`}><span>{f.n} {f.short}</span></button>)}
      </nav>
      {t !== TODAY_T && panel !== 'season' && panel !== 'compare' && !briefOpen && <div className="date-banner" data-testid="date-banner" role="status" style={phone ? undefined : { left: `calc(50% + ${(leftInset - rightInset) / 2}px)` }}><span>Showing <b>{tLabel(t)}</b></span><button className="btn btn-secondary btn-sm" onClick={() => { setT(TODAY_T); setPlaying(false); }}>Back to today</button></div>}

      {leftPanel === 'card' && selected && <FieldPanel onSheet={setSheetPx} onSpotRetry={selected.mine ? () => mf.retry(selected.id) : selected.spot ? () => tapSpot(selected.spot!.lat, selected.spot!.lon) : undefined} onMine={(a) => draw.current?.[a === 'delete' ? 'del' : a](selected)} loc={selected} prov={prov} cal={d?.cal ?? null} regional={regional} regionalLive={regionalLive} strategies={strats} onToday={(sid) => pickToday(selected.id, sid)} allocation={allocation[selected.id]} exampleLimit={exampleLimit} daily={dl?.daily ?? null}
        nasa={d?.nasa ?? null} nasaNow={d?.nasaNow ?? null} extras={d?.extras ?? { openet: null, stress: null, insurance: null, water: null }} iss={issNow} dataState={d ? 'ready' : timedOut === selected.id ? 'timeout' : 'loading'} dailyState={dl?.daily ? 'ready' : dl || timedOut === selected.id ? 'timeout' : 'loading'}
        t={t} setT={setT} events={events} onStep={onStep} onBack={() => goStep('pick')} setAllocation={(v) => setAllocation({ ...allocation, [selected.id]: v })} onClose={() => setCardOpen(false)} />}
      {leftPanel === 'fields' && <FieldPicker lands={lands} activeLandId={landId} onPickLand={openLand} tab={pickTab} setTab={setPickTab} onSheet={setSheetPx} mine={mf.locs} onDraw={() => draw.current?.start()} catalog={catalog} catGroup={catGroup} setCatGroup={setCatGroup} onCatalogPick={pickCatalog} locations={locations.filter((l) => !api.isSpot(l.id) && !l.mine)} live={live} strips={strips} selectedId={selectedId} onSelect={select} onBC={goBC} onExample={() => openExample()} onNationExample={() => tapSpot(33.51, -116.12)} onNationsExample={openNationsExample} onClose={panel === 'fields' ? () => setPanel('none') : undefined} />}
      {leftPanel === 'land' && land && <LandPanel land={land} presets={locations.filter((l) => !api.isSpot(l.id) && !l.mine)} onSheet={setSheetPx} onClose={() => setLandId(null)} onOpenSpot={tapSpot} onOpenField={select} onOpenFarm={mf.openShared} />}
      {selected && !leftPanel && !yearExpanded && !drawing && panel === 'none' && <button className="reopen btn btn-outline" onClick={() => setCardOpen(true)}><Icon name="info" size={16} />{fieldName(selected)}</button>}

      {stepPanel && !briefOpen && panel === 'season' && selected && d && <ComingSeason onSheet={setSheetPx} onBack={() => goStep('now')} nasaNow={d.nasaNow} regional={regional} regionalLive={regionalLive} loc={selected} outlook={ol} cal={d.cal} daily={dl?.daily ?? null} strategies={strats!} allocation={allocation[selected.id]} exampleLimit={exampleLimit} prov={prov} onCompare={() => setPanel('compare')} onClose={() => { if (sim) stopSim(); setPanel('none'); setBriefOpen(false); setCardOpen(false); }} />}
      {stepPanel && !briefOpen && panel === 'compare' && selected && d && <ComparePanel todayId={selected ? todayPick[selected.id] : null} onSheet={setSheetPx} onBack={() => goStep('season')} onLimit={() => goStep('now')} loc={selected} strategies={strats!} daily={dl?.daily ?? null} allocation={allocation[selected.id]} exampleLimit={exampleLimit} live={!!live} cal={d.cal} setAllocation={(v) => setAllocation({ ...allocation, [selected.id]: v })}
        onBrief={(id) => { setBriefPick(id); setBriefOpen(true); }} sim={sim} simRunning={!!sim && playing} onRunSim={runSim} onStopSim={stopSim} onClose={() => { if (sim) stopSim(); setPanel('none'); setBriefOpen(false); setCardOpen(false); }} />}

      {sim && selected && d?.cal && (
        <div className="sim-dock" data-testid="sim-dock" style={phone ? undefined : { left: `calc(50% + ${(leftInset - rightInset) / 2}px)` }}>
          <FieldTimeline t={t} setT={setT} playing={playing} setPlaying={setPlaying} cal={d.cal} events={events} sim={sim} />
        </div>
      )}

      {!drawing && !listOpen && <button className="list-btn btn btn-secondary" onClick={() => { announce('draw'); setListOpen(true); }} data-testid="list-btn" style={{ right: 16 + rightInset + 176 }}><Icon name="fields" size={18} />List</button>}
      {listOpen && <MapList locations={locations} catalog={catalog?.items ?? []} reserves={reserveRows} onClose={() => setListOpen(false)}
        onField={(id) => { setListOpen(false); select(id); }} onFarm={(it) => { setListOpen(false); pickCatalog(it); }}
        onReserve={(r) => { setListOpen(false); map.current?.flyTo(r.lat, r.lon, 11); }} onFind={(lat, lon) => { setListOpen(false); tapSpot(lat, lon); }} />}
      {aboutOpen && <AccessibilityPage onClose={() => setAboutOpen(false)} />}
      {layersOpen && <LayersDrawer landsCount={lands?.length ?? null} datasets={datasets} on={layersOn} toggle={(id) => setLayersOn({ ...layersOn, [id]: !layersOn[id] })} loc={selected} reserves={!!selected && api.isBC(selected)} onClose={() => setLayersOpen(false)} />}

      {stackField && !drilled && panel !== 'compare' && panel !== 'season' && view.zoom > 9.5 && view.zoom <= 13.4 && (
        <button className="hud glass drill-hint" data-testid="drill-hint" onClick={() => onStep('drill')}>
          <span className="hud-title"><Icon name="cube" size={16} />Scroll in (or tap) to look under the field</span>
        </button>
      )}
      {drilled && panel !== 'compare' && panel !== 'season' && (
        <div className="hud glass" data-testid="hud">
          <span className="hud-title"><Icon name="cube" size={16} />Under the field</span>
          <div className="hud-legend">
            <span><i style={{ background: '#7ee081' }} />Cover</span>
            <span><i style={{ background: '#5ab0ff' }} />Soil moisture</span>
            <span><i style={{ background: '#ff7eb6' }} />Groundwater</span>
            <span className="hud-note">taller = greener</span>
          </div>
        </div>
      )}
            {bc && !hasBC && (bcOpen || nearBC) && panel === 'none' && <div className="bc-float" style={{ left: `calc(${leftInset}px + 24px)` }}><BCCard bc={bc} floating onClose={bcOpen ? () => setBcOpen(false) : undefined} /></div>}

      <div className="controls" style={{ right: 16 + rightInset, bottom: bottomInset + 14 }}>
        <button className="ctl ctl-desk glass" onClick={goHome} title="Whole of California" aria-label="Show all of California"><Icon name="home" size={18} /></button>
        <button className="ctl ctl-desk glass" onClick={() => { if (!layersOpen) announce('layers'); setLayersOpen(!layersOpen); }} title="Map layers" aria-label="Map layers" aria-expanded={layersOpen} data-testid="layers-ctl"><Icon name="layers" size={18} /></button>
        {selected && d?.cal && <button className="ctl glass" onClick={() => { if (canReplay) startReplay(); else setPlaying(!playing); }} title={playing || replaying ? 'Pause' : 'Play the seasons'} aria-label={playing || replaying ? 'Pause the replay' : 'Play the seasons on the map'} aria-pressed={playing || replaying} data-testid="play-ctl"><Icon name={playing || replaying ? 'pause' : 'play'} size={18} /></button>}
        <button className="ctl glass" onClick={() => map.current?.resetNorth()} title="Reset north" aria-label="Reset north to the top"><span style={{ transform: `rotate(${-view.bearing - 45}deg)`, display: 'flex' }}><Icon name="compass" size={20} /></span></button>
        <button className="ctl glass text" onClick={() => map.current?.toggle3D()} title="Tilt" aria-label={view.pitch > 5 ? 'Flat map view' : 'Tilt the map to 3D'} data-testid="tilt">{view.pitch > 5 ? '2D' : '3D'}</button>
        <div className="ctl-group glass">
          <button onClick={() => map.current?.zoomBy(1)} title="Zoom in" aria-label="Zoom in"><Icon name="plus" size={18} /></button>
          <button onClick={() => map.current?.zoomBy(-1)} title="Zoom out" aria-label="Zoom out"><Icon name="minus" size={18} /></button>
        </div>
      </div>

      {!drawing && <WeatherControl on={wxOn} setOn={setWxOn} layer={wxLayer} setLayer={setWxLayer} mode={rainMode} setMode={setRainMode} days={rainDays} setDays={setRainDays} rain={rainNow ?? (rainHourly ? steps.find(Boolean) ?? null : null)} drought={droughtNow} region={dRegion} state={rainState} right={16 + rightInset} />}
      {rainHourly && !sim && <RainTimeline step={rainStep} setStep={setRainStep} playing={rainPlaying} setPlaying={setRainPlaying} steps={steps} loaded={stepsDone} left={phone ? '50%' : `calc(50% + ${(leftInset - rightInset) / 2}px)`} />}
      <DrawLayer ref={draw} getMap={() => map.current?.getMap() ?? null} mf={mf} rightInset={rightInset} onActive={(on, hideId) => { if (on) announce('draw'); setDrawing(on ? { hideId: hideId ?? null } : null); }}
        onSubmitting={onSubmitting} onSaved={onSaved} onDeleted={(id) => { if (selectedId === id) { setSelectedId(null); setPanel('none'); } }} onOpenShared={openMine} />

      {yearExpanded && selected && d?.cal && (
        <div className="year-dock" data-testid="year-dock">
          <YearSheet t={t} setT={setT} loc={selected} cal={d.cal} daily={dl?.daily ?? null} ml={d.ml} extras={d.extras} calSource={calSource(d.prov.calendar)} events={events}
            canReplay={canReplay} replaying={replaying} onReplay={startReplay} playing={playing} setPlaying={setPlaying} showEarlier={showEarlier} setShowEarlier={setShowEarlier} setExpanded={(b) => setYearOpen(b)} />
        </div>
      )}

      {stepPanel && briefOpen && selected && d && <BriefStep loc={selected} strategies={strats!} pick={briefPick} setPick={setBriefPick} allocation={allocation[selected.id]} exampleLimit={exampleLimit} onPreview={() => setBriefPreview(true)} onSheet={setSheetPx}
        onBack={() => goStep('compare')} onClose={() => { if (sim) stopSim(); setPanel('none'); setBriefOpen(false); setCardOpen(false); }} />}
      {briefOpen && selected && d && <RotationBrief preview={briefPreview} loc={selected} strategies={strats!} pick={briefPick} setPick={setBriefPick} allocation={allocation[selected.id]} exampleLimit={exampleLimit} prov={prov} outlook={ol} nasaNow={d.nasaNow} cal={d.cal} daily={dl?.daily ?? null} onClose={() => setBriefPreview(false)} />}
    </div>
    </DetailCtx.Provider>
  );
}
