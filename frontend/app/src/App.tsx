import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import MapView, { type MapHandle } from './MapView';
import * as api from './api';
import type { Dataset, FieldEvent, Location } from './types';
import { TODAY_T } from './lib';
import type { Daily } from './season';
import Icon from './components/Icons';
import ComingSeason from './components/season/ComingSeason';
import ComparePanel from './components/compare/ComparePanel';
import RotationBrief from './components/brief/RotationBrief';
import { LayersDrawer } from './components/Panels';
import { FieldPanel, FieldPicker } from './components/ui/Options';
import { setGlossary } from './components/ui/What';
import { DetailCtx, useDetailState } from './components/ui/Detail';
import { DockProvider } from './components/ui/Dock';
import { FLOW, acres, fieldName, placeLabel, type Step } from './components/ui/shared';
import { CedarChat } from './components/ui/Cedar';
import { FieldTimeline, type SimMode } from './components/ui/FieldTimeline';

/** Left dock for the decision; bottom dock for meters / compare results. */
type CoreStep = 'pick' | 'now' | 'season' | 'compare' | 'brief';
const SIDE_W = 360;
const LAYERS_OFF = { hls: false, smap: false, grace: false, imerg: false, modis: false, ecostress: false };

export default function App() {
  const [detail, setDetail] = useDetailState();
  const map = useRef<MapHandle>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const [locations, setLocations] = useState<Location[]>([]);
  const [locProv, setLocProv] = useState<Record<string, api.ProvMap>>({});
  const [live, setLive] = useState<boolean | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [data, setData] = useState<api.FieldBundle | null>(null);
  const [t, setT] = useState(TODAY_T);
  const [playing, setPlaying] = useState(false);
  const [sim, setSim] = useState<SimMode>(null);
  const [daily, setDaily] = useState<{ id: string; daily: Daily | null; prov: api.Prov } | null>(null);
  const [outlook, setOutlook] = useState<{ id: string; o: api.Outlook } | null>(null);
  const [iss, setISS] = useState<{ id: string; v: Awaited<ReturnType<typeof api.getISS>> } | null>(null);
  const [step, setStep] = useState<CoreStep>('pick');
  const [allocation, setAllocation] = useState<Record<string, number>>({});
  const [briefPick, setBriefPick] = useState<string | null>(null);
  const [timedOut, setTimedOut] = useState<string | null>(null);
  const [strips, setStrips] = useState<Record<string, Record<number, string>>>({});
  const [switchOpen, setSwitchOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [layersOpen, setLayersOpen] = useState(false);
  const [layersOn, setLayersOn] = useState<Record<string, boolean>>({ ...LAYERS_OFF, hls: true, smap: true, grace: true });
  const [pitch, setPitch] = useState(0);
  const [bottomEl, setBottomEl] = useState<HTMLElement | null>(null);

  useEffect(() => {
    api.getLocations().then(({ locations: ls, prov, live: lv }) => {
      api.getStrips(ls.map((l) => l.id)).then(setStrips);
      setLocations(ls); setLocProv(prov); setLive(lv);
      setAllocation(Object.fromEntries(ls.map((l) => [l.id, l.water.allocation_input.value])));
    });
    api.getDatasets().then(setDatasets);
    api.getGlossary().then(setGlossary);
  }, []);

  useEffect(() => {
    if (!switchOpen) return;
    const off = (e: MouseEvent) => { if (!(e.target as HTMLElement).closest('.tb-switch')) setSwitchOpen(false); };
    document.addEventListener('mousedown', off);
    return () => document.removeEventListener('mousedown', off);
  }, [switchOpen]);

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

  const alloc = selected ? allocation[selected.id] : undefined;
  useEffect(() => {
    if (!selected || !live || alloc == null || !data || data.prov.strategies.origin !== 'api') return;
    const h = setTimeout(() => api.scoreStrategies(selected.id, alloc).then((st) => st && setData((d) => {
      if (!d || d.id !== selected.id) return d;
      const keep = (s: (typeof st)[number]) => {
        const prev = d.strategies.find((x) => x.id === s.id);
        return s.water.etc_vs_openet_pct || !prev ? s : { ...s, water: { ...s.water, etc_vs_openet_pct: prev.water.etc_vs_openet_pct, openet_et_mm_season: prev.water.openet_et_mm_season } };
      };
      return { ...d, strategies: st.map(keep) };
    })), 450);
    return () => clearTimeout(h);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [alloc, selected, live, data?.id]);

  const select = useCallback((id: string) => {
    const loc = locations.find((l) => l.id === id);
    if (!loc) return;
    setSelectedId(id);
    setStep('now');
    setSwitchOpen(false);
    setQuery('');
    setPlaying(false);
    setSim(null);
    map.current?.flyToField(loc, 'card');
  }, [locations]);

  const stopSim = useCallback(() => {
    setPlaying(false);
    setSim(null);
    setT(TODAY_T);
  }, []);

  const runSim = useCallback((next: NonNullable<SimMode>, startT: number) => {
    setSim(next);
    setT(startT);
    setPlaying(true);
    setStep('compare');
  }, []);

  const d = data && data.id === selectedId ? data : null;
  useEffect(() => { (window as unknown as Record<string, unknown>).__app = { setT, select, ready: !!d, setStep }; }, [d, select]);
  const dl = daily && daily.id === selectedId ? daily : null;
  const ol = outlook && outlook.id === selectedId ? outlook.o : null;
  const issNow = iss && iss.id === selectedId ? iss.v : null;
  const regional = d?.regional ?? null;
  const regionalLive: api.RegionalLive = d?.regionalLive ?? { smap: false, grace: false, soilSource: null };
  const exampleLimit = !!selected && allocation[selected.id] === api.EXAMPLE_LIMIT[selected.id];
  const prov: api.ProvMap = { ...(selected ? locProv[selected.id] : {}), ...(d?.prov ?? {}), ...(dl ? { daily: dl.prov } : {}), ...(ol ? { outlook_cpc: ol.prov.cpc, outlook_water: ol.prov.water, outlook_alloc: ol.prov.alloc } : {}) };
  const events: FieldEvent[] = useMemo(() => (selected ? selected.events : []), [selected]);

  const goHome = () => { setSelectedId(null); setStep('pick'); setSwitchOpen(false); setLayersOpen(false); setPlaying(false); setSim(null); setT(TODAY_T); map.current?.flyHome(); };

  const goStep = (s: CoreStep) => {
    if (s !== 'pick' && !selected) { setStep('pick'); return; }
    setStep(s);
  };

  const onStep = (s: Step) => {
    if (s === 'season') goStep('season');
    else if (s === 'compare') goStep('compare');
    else if (s === 'brief') goStep('brief');
  };

  const toggle3D = () => {
    const on = pitch <= 5;
    if (on) {
      setLayersOn((L) => ({ ...L, hls: true, smap: true, grace: true }));
      if (selected) map.current?.flyToField(selected, 'drill');
      else map.current?.toggle3D();
    } else {
      map.current?.toggle3D();
    }
  };

  const q = query.trim().toLowerCase();
  const menuLocs = locations.filter((l) => !q || `${fieldName(l)} ${placeLabel(l)}`.toLowerCase().includes(q));
  const rightInset = layersOpen ? 340 : 0;
  const in3D = pitch > 5;

  return (
    <DetailCtx.Provider value={{ on: detail, set: setDetail }}>
    <DockProvider el={bottomEl}>
    <div className={`app ${detail ? 'detail-on' : 'detail-off'} core-mode dock`} data-testid="app-dock">
      <header className="topbar" data-testid="topbar">
        <button className="tb-brand" onClick={goHome} title="CropLytics home">CropLytics</button>
        <div className={`tb-switch ${switchOpen ? 'open' : ''}`}>
          <button className="tb-field" onClick={() => { setSwitchOpen(!switchOpen); setTimeout(() => searchRef.current?.focus(), 0); }} data-testid="field-switch" aria-expanded={switchOpen}>
            <span>
              <small>{selected ? placeLabel(selected) : 'No field picked'}</small>
              <b>{selected ? fieldName(selected) : 'Pick your field'}</b>
            </span>
            <Icon name="down" size={16} />
          </button>
          {switchOpen && (
            <div className="tb-menu" data-testid="field-menu">
              <div className="tb-search"><Icon name="search" size={16} />
                <input ref={searchRef} value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search fields" aria-label="Search fields" />
              </div>
              {menuLocs.map((l) => (
                <button key={l.id} type="button" className={l.id === selectedId ? 'on' : ''} onClick={() => select(l.id)}>
                  <b>{fieldName(l)}</b>
                  <small>{placeLabel(l)} · {acres(l)} acres</small>
                </button>
              ))}
              {menuLocs.length === 0 && <p className="muted" style={{ padding: '8px 10px' }}>No fields match.</p>}
            </div>
          )}
        </div>
        <nav className="tb-tabs" aria-label="Steps">
          {FLOW.map((s) => {
            const id = s.id as CoreStep;
            const locked = id !== 'pick' && !selected;
            return (
              <button key={s.id} type="button" className={step === id ? 'on' : ''} disabled={locked}
                onClick={() => goStep(id)} data-testid={`tab-${s.id}`} title={locked ? 'Pick a field first' : s.does}>
                <span className="tb-long">{s.n}. {s.short}</span>
                <span className="tb-short">{s.short}</span>
              </button>
            );
          })}
        </nav>
        <div className="tb-right">
          <button className={`tb-layers ${layersOpen ? 'on' : ''}`} onClick={() => setLayersOpen(!layersOpen)} data-testid="layers-btn" disabled={!selected} title={selected ? 'Show NASA layers on the map' : 'Pick a field first'}>
            <Icon name="layers" size={16} />Map layers
          </button>
        </div>
      </header>

      <div className="dock-row">
        <aside className="sidebar" style={{ width: SIDE_W }} data-testid="sidebar">
          <div className="side-body" data-testid="side-body">
            {step === 'pick' && (
              <FieldPicker locations={locations} live={live} strips={strips} selectedId={selectedId} onSelect={select} onBC={() => {}} />
            )}
            {step === 'now' && selected && (
              <FieldPanel key={selected.id} loc={selected} prov={prov} cal={d?.cal ?? null} regional={regional} regionalLive={regionalLive} strategies={d?.strategies ?? null} allocation={allocation[selected.id]} exampleLimit={exampleLimit} daily={dl?.daily ?? null}
                nasa={d?.nasa ?? null} nasaNow={d?.nasaNow ?? null} extras={d?.extras ?? { openet: null, stress: null, insurance: null, water: null }} iss={issNow} news={d?.news ?? []} dataState={d ? 'ready' : timedOut === selected.id ? 'timeout' : 'loading'} dailyState={dl?.daily ? 'ready' : dl || timedOut === selected.id ? 'timeout' : 'loading'}
                t={t} setT={setT} events={events} onStep={onStep} onClose={() => goStep('pick')} />
            )}
            {step === 'season' && selected && d && (
              <ComingSeason nasaNow={d.nasaNow} regional={regional} regionalLive={regionalLive} loc={selected} outlook={ol} cal={d.cal} daily={dl?.daily ?? null} strategies={d.strategies} allocation={allocation[selected.id]} exampleLimit={exampleLimit} prov={prov} onCompare={() => goStep('compare')} onClose={() => goStep('now')} />
            )}
            {step === 'compare' && selected && d && (
              <ComparePanel loc={selected} strategies={d.strategies} daily={dl?.daily ?? null} allocation={allocation[selected.id]} exampleLimit={exampleLimit} live={!!live} cal={d.cal} setAllocation={(v) => setAllocation({ ...allocation, [selected.id]: v })}
                onBrief={(id) => { setBriefPick(id); goStep('brief'); }} onClose={() => goStep('season')}
                sim={sim} simRunning={!!sim && playing} onRunSim={runSim} onStopSim={stopSim} />
            )}
            {step === 'brief' && selected && d && (
              <RotationBrief loc={selected} strategies={d.strategies} pick={briefPick} setPick={setBriefPick} allocation={allocation[selected.id]} exampleLimit={exampleLimit} prov={prov} outlook={ol} nasaNow={d.nasaNow} cal={d.cal} daily={dl?.daily ?? null} onClose={() => goStep('compare')} />
            )}
            {step !== 'pick' && !selected && (
              <p className="side-empty">Pick a field to continue.</p>
            )}
            {step !== 'pick' && selected && !d && step !== 'now' && (
              <p className="side-empty">Loading your field…</p>
            )}
          </div>
        </aside>

        <div className="dock-map-col">
          <main className="stage">
            <MapView ref={map} locations={locations} bc={null} datasets={datasets} selected={selected} cells={d?.cells ?? null} cal={d?.cal ?? null} regional={regional}
              t={t} detector="rule" metric="cover" regionalLive={regionalLive} layersOn={layersOn} leftInset={0} rightInset={rightInset} bottomInset={12}
              onSelect={select} onBC={() => {}} onView={(v) => setPitch(v.pitch)} />
            {in3D && selected && (
              <div className="hud glass" data-testid="stack-hud">
                <span className="hud-title"><Icon name="cube" size={16} />Under the field</span>
                <span className="hud-legend">
                  <span><i style={{ background: '#2f9e4b' }} />Cover</span>
                  <span><i style={{ background: '#3d97e8' }} />Soil moisture</span>
                  <span><i style={{ background: '#8a5a00' }} />Groundwater</span>
                </span>
              </div>
            )}
            {layersOpen && (
              <LayersDrawer datasets={datasets} on={layersOn} toggle={(id) => setLayersOn({ ...layersOn, [id]: !layersOn[id] })} loc={selected} onClose={() => setLayersOpen(false)} />
            )}
            <div className="controls" style={{ right: 12 + rightInset }}>
              <button className="ctl glass" onClick={goHome} title="Home"><Icon name="home" size={18} /></button>
              <div className="ctl-group glass">
                <button onClick={() => map.current?.zoomBy(1)} title="Zoom in"><Icon name="plus" size={18} /></button>
                <button onClick={() => map.current?.zoomBy(-1)} title="Zoom out"><Icon name="minus" size={18} /></button>
              </div>
              <button className={`ctl glass text ${in3D ? 'on' : ''}`} onClick={toggle3D} title="Tilt the map to see under the field" data-testid="tilt" disabled={!selected}>
                <Icon name="cube" size={16} />{in3D ? '2D' : '3D'}
              </button>
            </div>
            {selected && (
              <CedarChat ctx={{
                loc: selected,
                regional,
                strategies: d?.strategies ?? null,
                allocation: allocation[selected.id],
                takeaway: null,
              }} />
            )}
            {selected && d?.cal && (
              <FieldTimeline
                t={t}
                setT={setT}
                playing={playing}
                setPlaying={setPlaying}
                cal={d.cal}
                events={events}
                sim={sim}
              />
            )}
          </main>
          <aside className={`bottombar ${step === 'pick' ? 'idle' : ''}`} ref={setBottomEl} data-testid="bottombar">
            {step === 'pick' && <p className="bottom-hint">Tap a field on the left — or the pin on the map.</p>}
          </aside>
        </div>
      </div>
    </div>
    </DockProvider>
    </DetailCtx.Provider>
  );
}
