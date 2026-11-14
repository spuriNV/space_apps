import { useCallback, useMemo, useState } from 'react';
import { DEFAULT_WEIGHTS, MM_PER_AF_AC, PRIORITIES, getLocation, haToAc, scoreStrategies } from './api';
import type maplibregl from 'maplibre-gl';
import MapView from './MapView';
import type { MeasureKey } from './measures';
import type { CellProps, PriorityKey, Weights } from './types';
import TopBar from './components/TopBar';
import FieldCards from './components/FieldCards';
import RotationList from './components/RotationList';
import YearView from './components/YearView';
import CompareView, { type Replay } from './components/CompareView';
import BriefView from './components/BriefView';
import Inspector from './components/Inspector';
import { Icon, fmt } from './components/Bits';

type Tab = 'rotations' | 'year' | 'compare';

export default function App() {
  const [locId, setLocId] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>('rotations');
  const [weights, setWeights] = useState<Weights>(DEFAULT_WEIGHTS);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [allocByLoc, setAllocByLoc] = useState<Record<string, number>>({});
  const [briefId, setBriefId] = useState<string | null>(null);
  const [hoverId, setHoverId] = useState<string | null>(null);
  const [hoverStrategy, setHoverStrategy] = useState<string | null>(null);
  const [visible, setVisible] = useState<string[]>(['car_colusa_rice', 'caf_tulare_forage']);
  const [is3d, setIs3d] = useState(false);
  const [measure, setMeasure] = useState<MeasureKey>('ndvi');
  const [cell, setCell] = useState<CellProps | null>(null);
  const [basemapPick, setBasemapPick] = useState<'map' | 'satellite' | null>(null);
  const [detector, setDetector] = useState<'rule' | 'ml'>('rule');
  const [replay, setReplay] = useState<Replay>('typical');
  const [zoom, setZoom] = useState(5);

  const loc = locId ? getLocation(locId) : null;
  const allocation = loc ? allocByLoc[loc.id] ?? loc.water.allocation_input.value : 0;
  const scored = useMemo(() => (locId ? scoreStrategies(locId, weights) : []), [locId, weights]);
  const basemap = basemapPick ?? (loc ? 'satellite' : 'map'); // streets for finding a field, imagery once you are on it (unless the user chose)
  const hot = PRIORITIES.filter((p) => weights[p.key] > 1);
  const sortLabel = hot.length ? `sorted for ${hot.map((p) => p.label.toLowerCase()).join(', ')}` : 'sorted by overall fit, all priorities equal';

  const openField = useCallback((id: string) => {
    setLocId(id); setTab('rotations'); setIs3d(false); setCell(null); setBriefId(null); setReplay('typical');
    setCompareIds(scoreStrategies(id, DEFAULT_WEIGHTS).map((s) => s.id));
  }, []);
  const home = useCallback(() => { setLocId(null); setIs3d(false); setCell(null); setBriefId(null); }, []);
  const togglePriority = (k: PriorityKey) => setWeights((w) => ({ ...w, [k]: w[k] > 1 ? 1 : 4 }));
  const toggleCompare = (id: string) => setCompareIds((ids) => (ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]));
  const set3d = useCallback((v: boolean) => { setIs3d(v); if (!v) setCell(null); }, []);
  const enter3d = () => { const map = (window as unknown as { __map: maplibregl.Map }).__map; if (loc) map.easeTo({ center: [loc.centroid.lon, loc.centroid.lat], zoom: 15.25, duration: 900 }); };
  const compared = scored.filter((s) => compareIds.includes(s.id)).sort((a, b) => Number(b.is_baseline) - Number(a.is_baseline) || a.rank - b.rank);
  const wide = !!loc && tab === 'compare';

  return (
    <div className="app">
      <TopBar weights={weights} onToggle={togglePriority} onOpen={openField} onHome={home} fieldName={loc ? loc.short_name : null} />
      <div className={`work${wide ? ' wide' : ''}`}>
        <aside className="list">
          {!loc && <FieldCards visible={visible} hoverId={hoverId} onHover={setHoverId} onOpen={openField} />}
          {loc && (
            <div className="pane">
              <div className="fieldhead">
                <button className="backlink" onClick={home} data-action="back"><Icon name="back" size={15} />All fields</button>
                <div className="fh-row">
                  <div>
                    <h1>{loc.short_name}</h1>
                    <p>{loc.region_label} · {fmt(loc.area_ha.value)} ha ({fmt(haToAc(loc.area_ha.value))} acres) · {loc.soil.texture_class.toLowerCase()}, {loc.soil.drainage_class.toLowerCase()}</p>
                  </div>
                  <div className="alloc" title="Your water allocation for the season. Rotations are checked against this number.">
                    <label>Water allocation</label>
                    <div className="stepper">
                      <button onClick={() => setAllocByLoc({ ...allocByLoc, [loc.id]: Math.max(0.5, +(allocation - 0.5).toFixed(1)) })} aria-label="Lower allocation"><Icon name="minus" size={14} /></button>
                      <span><b>{fmt(allocation, 1)}</b> acre-ft/acre</span>
                      <button onClick={() => setAllocByLoc({ ...allocByLoc, [loc.id]: Math.min(6, +(allocation + 0.5).toFixed(1)) })} aria-label="Raise allocation"><Icon name="plus" size={14} /></button>
                    </div>
                    <small>{fmt(allocation * MM_PER_AF_AC)} mm · {loc.water.district}</small>
                  </div>
                </div>
                <nav className="tabs" role="tablist">
                  <button role="tab" aria-selected={tab === 'rotations'} onClick={() => setTab('rotations')} data-tab="rotations">Rotations <i>{scored.length}</i></button>
                  <button role="tab" aria-selected={tab === 'year'} onClick={() => setTab('year')} data-tab="year">Your field's year</button>
                  <button role="tab" aria-selected={tab === 'compare'} onClick={() => setTab('compare')} data-tab="compare" disabled={compared.length < 2}>Compare <i>{compared.length}</i></button>
                </nav>
              </div>
              {tab === 'rotations' && <RotationList items={scored} allocation={allocation} compareIds={compareIds} onToggleCompare={toggleCompare} onBrief={setBriefId} onCompare={() => setTab('compare')} sortLabel={sortLabel} hoverId={hoverStrategy} onHover={setHoverStrategy} />}
              {tab === 'year' && <YearView loc={loc} detector={detector} onDetector={setDetector} />}
              {tab === 'compare' && compared.length >= 2 && <CompareView items={compared} allocation={allocation} replay={replay} onReplay={setReplay} onBrief={setBriefId} onRemove={toggleCompare} weights={weights} />}
            </div>
          )}
        </aside>
        <section className={`mapwrap${is3d ? ' is3d' : ''}`}>
          <MapView loc={loc} hoverId={hoverId} is3d={is3d} measure={measure} basemap={basemap} selectedCell={cell?.id ?? null}
            onHover={setHoverId} onOpen={openField} onVisible={setVisible} onSet3d={set3d} onSelectCell={setCell} onZoom={setZoom} />
          {loc && !is3d && !wide && (
            <button className="hintchip" onClick={enter3d} data-action="enter-3d"><Icon name="cube" size={16} />Scroll in to see this field as a 3D block</button>
          )}
          {loc && !is3d && wide && <button className="hintchip sm" onClick={enter3d}><Icon name="cube" size={15} />3D block</button>}
          {!loc && zoom > 7.5 && <button className="hintchip" onClick={home}>Back to all of California</button>}
          <button className={`basetile to-${basemap === 'map' ? 'satellite' : 'map'}`} onClick={() => setBasemapPick(basemap === 'map' ? 'satellite' : 'map')} aria-label="Switch base map" data-action="basemap">
            <span><Icon name="layers" size={13} />{basemap === 'map' ? 'Satellite' : 'Map'}</span>
          </button>
          {loc && is3d && <Inspector loc={loc} measure={measure} onMeasure={setMeasure} cell={cell} onExit={() => set3d(false)} />}
        </section>
      </div>
      {loc && briefId && <BriefView loc={loc} items={scored} id={briefId} allocation={allocation} onPick={setBriefId} onClose={() => setBriefId(null)} />}
    </div>
  );
}
