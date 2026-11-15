// One farmer-first field panel. Order: what this field is -> "Your field now" answers -> next steps -> More detail (about the
// ground, last 3 seasons, sources). A floating paper card on a desktop (the field name collapses into a sticky one-line bar
// on scroll; the one primary action sits in the footer); a draggable bottom sheet on a phone (peek, half, full).
import type { Calendar, FieldEvent, Location, Regional, RotationStrategy } from '../../types';
import { bcGap, isBC, type Extras, type ISSPhoto, type NasaNow, type ProvMap, type RegionalLive } from '../../api';
import type { NasaDataset } from '../../nasa';
import { ISSFigure, NasaList } from './NasaSection';
import { SourcesSheet } from './Sources';
import { MoreDetail } from './Detail';
import type { Daily } from '../../season';
import Icon from '../Icons';
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type PointerEvent as RPointerEvent, type KeyboardEvent as RKeyboardEvent } from 'react';
import { AboutField, Actions, CROP_COL, EventLog, NextSteps, PrimaryAction, acres, coords, county, cropName, fieldCode, fieldName, latestCrop, place, type Step } from './shared';
import { FirstNationsCard } from './FirstNations';
import { SalmonPanel } from '../salmon/SalmonPanel';
import { FieldNow, LastSeasons, whenT, type LoadState } from './FieldNow';
import { MONTHS, TODAY_T } from '../../lib';

export interface FieldPanelProps {
  loc: Location; prov: ProvMap; cal: Calendar | null; regional: Regional | null; regionalLive: RegionalLive; strategies: RotationStrategy[] | null; allocation?: number; exampleLimit: boolean; daily: Daily | null;
  nasa: NasaDataset[] | null; nasaNow: NasaNow | null; extras: Extras; iss: { photo: ISSPhoto; credit: string } | null; dataState: LoadState; dailyState: LoadState;
  t: number; setT: (t: number) => void; events: FieldEvent[];
  onStep: (s: Step) => void; onClose: () => void;
  /** phone: how much of the sheet shows above the tab bar, so the map keeps the field in view */
  onSheet?: (visiblePx: number) => void;
  /** a tapped spot whose analysis failed: try again */
  onSpotRetry?: () => void;
}

export function FieldPanel(p: FieldPanelProps) {
  const { loc } = p;
  const thumbs = useThumbs();
  const [src, setSrc] = useState(false);
  const sheet = useSheet(p.onSheet);
  const scrollRef = useRef<HTMLDivElement>(null);
  const headRef = useRef<HTMLElement>(null);
  const [stuck, setStuck] = useState(false); // the field name has scrolled under the top: show the one-line bar
  const [footStuck, setFootStuck] = useState(false); // content runs on under the footer
  const onScroll = useCallback(() => {
    const el = scrollRef.current, h = headRef.current;
    if (!el) return;
    setStuck(el.scrollTop > (h ? h.offsetHeight - 40 : 8));
    setFootStuck(el.scrollTop + el.clientHeight < el.scrollHeight - 1);
  }, []);
  // a new field: back to the top, the sources sheet closed, the content cross-fades in (.fp-content is keyed by field)
  useEffect(() => { scrollRef.current?.scrollTo({ top: 0 }); setSrc(false); onScroll(); }, [loc.id, onScroll]);
  useEffect(() => { const h = setTimeout(onScroll, 400); return () => clearTimeout(h); }, [p.dataState, p.dailyState, onScroll]);
  // below full the sheet's content does not scroll: bring it back to the top
  useEffect(() => { if (sheet.snap !== 'full') scrollRef.current?.scrollTo({ top: 0, behavior: 'smooth' }); }, [sheet.snap]);
  const now = latestCrop(loc);
  const sp = loc.spot;
  const isToday = p.t === TODAY_T;
  const crop = cropName(now.crop);
  return (
    <section ref={sheet.ref} className={`panel fpanel sheet-${sheet.snap} ${stuck ? 'stuck' : ''}`} data-testid="field-panel" aria-label={fieldName(loc)} {...sheet.handlers}>
      <button className="fp-grab" onClick={sheet.cycle} onKeyDown={sheet.onKey} aria-label="Resize the field panel" data-testid="grab"><i /></button>
      <div className="fp-body">
        <div className="fp-bar" aria-hidden={!stuck}><span className="fp-bar-title">{fieldName(loc)}</span></div>
        <button className="icon-btn fp-close" onClick={p.onClose} title="Close" aria-label="Close"><Icon name="close" size={20} /></button>
        <div className="panel-scroll" ref={scrollRef} onScroll={onScroll}>
          <div className="fp-content" key={loc.id}>
            <header className="fp-head" ref={headRef}>
              {sp && <p className="spot-label" data-testid="spot-label"><i className={`live-dot ${sp.state}`} />Tapped spot · live data</p>}
              <h1>{fieldName(loc)}</h1>
              {sp?.state === 'loading' ? <p className="fp-facts"><span className="skel skel-chip" /><span className="skel skel-chip" /><span className="skel skel-chip" /></p> : sp?.state === 'error' ? null : (
              <p className="fp-facts">
                <span className="fact-chip"><b>{acres(loc)}</b> acres</span>
                {now.year != null && Number.isFinite(now.year) && <span className="fact-chip"><i style={{ background: CROP_COL(crop) }} />{now.crop.charAt(0).toUpperCase() + now.crop.slice(1).toLowerCase()} in {now.year}</span>}
                <span className="fact-chip">{place(loc)}</span>
              </p>)}
              <p className="fp-id">{sp ? (sp.fallbackSquare || sp.state !== 'ready' ? '200 m square around your tap, not a field outline' : loc.dwr_id ? `State field no. ${loc.dwr_id}` : 'Field outline at your tap') : isBC(loc) ? 'British Columbia' : fieldCode(loc).replace('DWR ', 'State field no. ')}, {coords(loc)}</p>
            </header>
            {sp?.state === 'error' && <div className="notice spot-notice" role="alert" data-testid="spot-error"><span>{sp.error}</span>{p.onSpotRetry && <button className="btn btn-outline btn-sm" onClick={p.onSpotRetry}>Try again</button>}</div>}
            {sp?.state === 'ready' && sp.cropland === false && <div className="notice spot-notice" data-testid="spot-not-farm"><b>This may not be farmland.</b> The USDA crop map shows little or no cropping here, so the rotations below are a stand-in.</div>}
            <Actions onStep={p.onStep} />
            <h2 className="fp-h">{isToday ? 'Your field now' : 'Your field in ' + whenT(p.t)}</h2>
            <FieldNow dataState={p.dataState} dailyState={p.dailyState} thumb={thumbs?.[loc.id] ?? null} extras={p.extras} nasaNow={p.nasaNow} loc={loc} cal={p.cal} regional={p.regional} regionalLive={p.regionalLive} strategies={p.strategies} allocation={p.allocation} exampleLimit={p.exampleLimit} t={p.t} daily={p.daily} prov={p.prov} />
            {isBC(loc) && <FirstNationsCard loc={loc} />}
            {isBC(loc) && <SalmonPanel locId={loc.id} />}
            <NextSteps onStep={p.onStep} />
            <MoreDetail what="Sources, past seasons, 3D" />
            <div className="fp-more">
              <div className="fp-more-in">
                <h2 className="fp-h" data-testid="nasa-section">NASA data behind this field</h2>
                <ISSFigure iss={p.iss} />
                {p.nasa ? <NasaList list={p.nasa} /> : <p className="muted">Loading…</p>}
                <h2 className="fp-h">About the ground<button className="btn btn-text btn-sm" onClick={() => p.onStep('drill')} data-testid="step-drill"><Icon name="cube" />Look under the field in 3D</button></h2>
                <AboutField loc={loc} prov={p.prov} cal={p.cal} insurance={p.extras.insurance ?? loc.rma ?? null} insGap={bcGap(loc, 'insurance')} />
                {!sp && <><h2 className="fp-h">The last 3 seasons</h2>
                <LastSeasons loc={loc} cal={p.cal} t={p.t} /></>}
                {p.events.length > 0 && <><h2 className="fp-h">What happened around here</h2><p className="fp-sub">Click one to move the timeline.</p><EventLog events={p.events} setT={p.setT} /></>}
                <button className="btn btn-text sources-link" onClick={() => setSrc(true)} data-testid="sources-link">Sources</button>
              </div>
            </div>
            <p className="footnote">CropLytics helps the grower and adviser decide; it does not replace either.</p>
          </div>
        </div>
      </div>
      <footer className={`fp-foot ${footStuck ? 'stuck' : ''}`}><PrimaryAction onStep={p.onStep} /></footer>
      {src && <SourcesSheet bc={isBC(loc)} onClose={() => setSrc(false)} />}
    </section>
  );
}

type Snap = 'peek' | 'half' | 'full';
const SNAPS: Snap[] = ['peek', 'half', 'full'];
const PHONE = '(max-width: 640px)';
/** Phone bottom sheet: snap points peek (128px), half (52% of the screen) and full. The sheet follows the finger by
 *  transform only; on release it goes to the nearest snap point, or to the next one in the direction of a fling
 *  (faster than 0.5 px/ms). Tap the handle to cycle; arrow keys on the handle step. Content scrolls only at full;
 *  below that, a drag anywhere on the sheet moves the sheet (the Google Maps behaviour). */
function useSheet(onSheet?: (visiblePx: number) => void) {
  const ref = useRef<HTMLElement>(null);
  const [snap, setSnap] = useState<Snap>('half');
  const drag = useRef<{ id: number; y0: number; off0: number; last: number; t: number; v: number; on: boolean } | null>(null);
  const dragged = useRef(false);
  const phone = () => window.matchMedia(PHONE).matches;
  const offOf = (s: Snap) => {
    const h = ref.current?.offsetHeight ?? 0;
    return s === 'full' ? 0 : Math.max(0, h - (s === 'half' ? Math.round(window.innerHeight * 0.52) : 128));
  };
  const curOff = () => { const el = ref.current; return el ? new DOMMatrixReadOnly(getComputedStyle(el).transform).m42 : 0; };
  const go = useCallback((s: Snap) => {
    const el = ref.current;
    if (!el || !phone()) return;
    el.style.setProperty('--sheet-off', `${offOf(s)}px`);
    setSnap(s);
    onSheet?.((el.offsetHeight ?? 0) - offOf(s));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onSheet]);
  // place the sheet before the first paint (the CSS entrance then slides it up from below), and again on resize
  useLayoutEffect(() => {
    const fit = () => { if (phone()) go(snap); else ref.current?.style.removeProperty('--sheet-off'); };
    fit();
    window.addEventListener('resize', fit);
    return () => window.removeEventListener('resize', fit);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snap]);
  const onPointerDown = (e: RPointerEvent) => {
    if (!phone() || (e.pointerType === 'mouse' && e.button !== 0)) return;
    const handle = (e.target as Element).closest('.fp-grab, .fp-bar, .fp-head');
    if (snap === 'full' && !handle) return; // at full the content scrolls; the handle and header still move the sheet
    drag.current = { id: e.pointerId, y0: e.clientY, off0: curOff(), last: e.clientY, t: e.timeStamp, v: 0, on: false };
    // a mouse drag from the handle or header keeps its moves even when it leaves the sheet (touch has implicit capture)
    if (handle && e.pointerType === 'mouse') (handle as HTMLElement).setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e: RPointerEvent) => {
    const d = drag.current, el = ref.current;
    if (!d || !el || e.pointerId !== d.id) return;
    const dy = e.clientY - d.y0;
    if (!d.on) {
      if (Math.abs(dy) < 6) return;
      if (snap === 'full' && dy < 0) { drag.current = null; return; } // already at the top: let the content scroll
      d.on = true; if (!el.hasPointerCapture(e.pointerId) && !(e.target as Element).hasPointerCapture?.(e.pointerId)) el.setPointerCapture(e.pointerId); el.classList.add('dragging');
    }
    const max = offOf('peek');
    let off = d.off0 + dy;
    if (off < 0) off = -Math.pow(-off, 0.7); // rubber band past the top and past peek
    else if (off > max) off = max + Math.pow(off - max, 0.7);
    el.style.setProperty('--sheet-off', `${off}px`);
    const dt = e.timeStamp - d.t;
    if (dt > 0) d.v = 0.7 * ((e.clientY - d.last) / dt) + 0.3 * d.v;
    d.last = e.clientY; d.t = e.timeStamp;
  };
  const onPointerUp = (e: RPointerEvent) => {
    const d = drag.current, el = ref.current;
    drag.current = null;
    if (!d || !d.on || !el) return;
    el.classList.remove('dragging');
    dragged.current = true; setTimeout(() => { dragged.current = false; }, 0);
    const off = curOff(), v = e.timeStamp - d.t > 90 ? 0 : d.v;
    const offs = SNAPS.map(offOf);
    let target: Snap;
    if (Math.abs(v) > 0.5) {
      // fling: the next snap point in that direction (down = a larger offset)
      const order = SNAPS.map((s, i) => ({ s, o: offs[i] })).sort((a, b) => a.o - b.o);
      const next = v > 0 ? order.find((x) => x.o > off + 1) ?? order[order.length - 1] : [...order].reverse().find((x) => x.o < off - 1) ?? order[0];
      target = next.s;
    } else target = SNAPS.reduce((a, s, i) => (Math.abs(offs[i] - off) < Math.abs(offs[SNAPS.indexOf(a)] - off) ? s : a), snap);
    go(target);
  };
  const handlers = {
    onPointerDown, onPointerMove, onPointerUp, onPointerCancel: onPointerUp,
    // a drag that started on a button must not also press it
    onClickCapture: (e: React.MouseEvent) => { if (dragged.current) { e.stopPropagation(); e.preventDefault(); } },
  };
  const cycle = () => { if (!dragged.current) go(snap === 'peek' ? 'half' : snap === 'half' ? 'full' : 'peek'); };
  const onKey = (e: RKeyboardEvent) => {
    const i = SNAPS.indexOf(snap), j = e.key === 'ArrowUp' ? Math.min(2, i + 1) : e.key === 'ArrowDown' ? Math.max(0, i - 1) : i;
    if (j !== i) { e.preventDefault(); go(SNAPS[j]); }
  };
  return { ref, snap, handlers, cycle, onKey };
}

/** "Pick your field": one paper surface, one row per field with a satellite thumbnail (outline drawn), a 2023-2026 season strip,
 *  one line of facts in grower units and one line of what is notable. A BC field the API serves sits under its own
 *  "British Columbia" heading (and chip); without one, BC is a quiet "not set up yet" row at the bottom. */
export function FieldPicker(p: { locations: Location[]; live: boolean | null; strips: Record<string, Record<number, string>>; selectedId: string | null; onSelect: (id: string) => void; onBC: () => void; onClose?: () => void }) {
  const thumbs = useThumbs();
  const [q, setQ] = useState('');
  const [fam, setFam] = useState<string | null>(null);
  const nBC = p.locations.filter(isBC).length;
  const fams = [...(['rice', 'forage'] as const).map((f) => ({ f: f as string, label: f === 'rice' ? 'Rice' : 'Forage', n: p.locations.filter((l) => familyOf(l) === f).length })), { f: 'bc', label: 'British Columbia', n: nBC }].filter((x) => x.n > 0);
  const words = q.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const hit = (l: Location) => (!fam || (fam === 'bc' ? isBC(l) : familyOf(l) === fam)) && words.every((w) => `${fieldName(l)} ${county(l)} ${isBC(l) ? 'british columbia bc' : 'county california'} ${latestCrop(l).crop} ${l.water?.district ?? ''}`.toLowerCase().includes(w));
  const shownCA = p.locations.filter((l) => !isBC(l) && hit(l)), shownBC = p.locations.filter((l) => isBC(l) && hit(l));
  const shown = [...shownCA, ...shownBC];
  return (
    <section className="picker2" data-testid="fields-panel">
      <header className="pk-head">
        <h1>Pick your field</h1>
        {p.onClose && <button className="icon-btn" onClick={p.onClose} title="Close" aria-label="Close"><Icon name="close" size={20} /></button>}
      </header>
      {p.locations.length > 1 && (
        <div className="pk-filter">
          <label className="pk-search"><Icon name="search" size={16} /><input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by town, county or crop" aria-label="Search fields" data-testid="pk-search" /></label>
          <div className="chips" role="group" aria-label="Crop">
            {fams.map(({ f, label, n }) => <button key={f} className="chip" aria-pressed={fam === f} onClick={() => setFam(fam === f ? null : f)} data-testid={`chip-${f}`}><Icon name="check" size={16} className="check" />{label} <span className="n">{n}</span></button>)}
          </div>
        </div>
      )}
      {p.live === false && <p className="notice offline-note" data-testid="offline-note">The CropLytics server is not answering, so every number is an example. Start the API (see the README) and reload for real data.</p>}
      {p.locations.length === 0 && <p className="loading-note">Loading the fields…</p>}
      {([['ca', shownCA], ['bc', shownBC]] as const).map(([rg, rows]) => rows.length > 0 && (
      <div key={rg}>
      {rg === 'bc' && <h2 className="pk-group" data-testid="pk-group-bc">British Columbia</h2>}
      <ul className="pk-list" data-testid={rg === 'bc' ? 'field-table-bc' : 'field-table'}>
        {rows.map((l) => {
          const now = latestCrop(l), th = thumbs?.[l.id], strip = p.strips[l.id];
          return (
            <li key={l.id}>
              <button className={`pk-row ${p.selectedId === l.id ? 'on' : ''}`} aria-current={p.selectedId === l.id ? 'true' : undefined} onClick={() => p.onSelect(l.id)} data-testid={`row-${l.id}`}>
                <span className="pk-thumb">
                  <img src={`${import.meta.env.BASE_URL}thumbs/${l.id}.jpg`} alt={`Satellite view of ${fieldName(l)}`} onError={(e) => { e.currentTarget.style.visibility = 'hidden'; }} />
                  {th && <svg viewBox="0 0 360 240" preserveAspectRatio="none" aria-hidden="true"><polygon points={outlinePts(l, th.bbox)} /></svg>}
                </span>
                <span className="pk-body">
                  <b>{fieldName(l)}</b>
                  <span className="pk-facts">{place(l)} · {acres(l)} acres · {now.crop.toLowerCase()} in {now.year}</span>
                  <span className="pk-note">{notable(l)}</span>
                  <span className="pk-strip" title="Bare, green or flooded, 2023 to 2026, from satellites">
                    {[2023, 2024, 2025, 2026].map((y) => <span key={y}><i>{(strip?.[y] ?? 'u'.repeat(36)).split('').map((c, k) => <em key={k} className={`c-${c}`} />)}</i><small>{y}</small></span>)}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      </div>
      ))}
      {p.locations.length > 0 && !shown.length && <p className="loading-note">No field matches. <button className="btn btn-outline btn-sm" onClick={() => { setQ(''); setFam(null); }}>Show all</button></p>}
      {p.locations.length > 0 && !nBC && <button className="pk-bc" onClick={p.onBC}>British Columbia: not set up yet. <u>See why</u></button>}
    </section>
  );
}
/** Crop family: from the API, else from the field id (car_ rice, caf_ forage). */
const familyOf = (l: Location) => l.family ?? (l.id.startsWith('car') ? 'rice' : l.id.startsWith('caf') ? 'forage' : 'other');
/** Field outline in thumbnail coordinates (360 x 240, plate carrée over a small box). */
function outlinePts(l: Location, b: number[]) {
  return l.geometry.coordinates[0].map(([x, y]) => `${(((x - b[0]) / (b[2] - b[0])) * 360).toFixed(1)},${(((b[3] - y) / (b[3] - b[1])) * 240).toFixed(1)}`).join(' ');
}
/** One line of what is notable about the field, from its record. */
function notable(l: Location) {
  const notes: string[] = [];
  // BC: the irrigation order is what is notable (no California water district)
  const order = l.water_context?.orders?.[0];
  if (l.region === 'bc') return order ? `Irrigation stopped by a fish-flow order in ${MONTHS[+order.date.slice(5, 7) - 1]} ${order.date.slice(0, 4)}.` : '';
  const fallow = Object.entries(l.crop_history).filter(([y, c]) => +y >= 2016 && cropName(c) === 'Left fallow').map(([y]) => +y);
  if (fallow.includes(2022)) notes.push('Left fallow in the 2022 drought');
  else if (fallow.length) notes.push(`Left fallow in ${fallow[fallow.length - 1]}`);
  if (l.water?.source === 'surface') notes.push(l.water_real && l.water.district ? `surface water, ${l.water.district}` : 'surface water');
  else if (l.water?.source) notes.push(/probation/i.test(l.water.sgma_status?.text ?? '') ? 'wells; basin on state probation' : 'wells');
  const s = notes.join('; ');
  return s ? s.charAt(0).toUpperCase() + s.slice(1) + '.' : '';
}

let thumbsP: Promise<Record<string, { bbox: number[] }>> | null = null;
/** Satellite thumbnails of each field (public/thumbs), with the bounds needed to draw the outline. */
function useThumbs() {
  const [t, setT] = useState<Record<string, { bbox: number[] }> | null>(null);
  useEffect(() => { (thumbsP ??= fetch(`${import.meta.env.BASE_URL}thumbs/thumbs.json`).then((r) => r.json()).then((j) => j.fields).catch(() => ({}))).then(setT); }, []);
  return t;
}
