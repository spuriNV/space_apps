// One farmer-first field panel. Order: what this field is -> "Your field now" answers -> about the ground -> last 3 seasons -> sources.
// The next steps sit in a fixed footer so they are always visible without scrolling.
import type { Calendar, FieldEvent, Location, Regional, RotationStrategy } from '../../types';
import { bcGap, isBC, type Extras, type ISSPhoto, type NasaNow, type ProvMap, type RegionalLive } from '../../api';
import type { NasaDataset } from '../../nasa';
import { ISSFigure, NasaList } from './NasaSection';
import { SourcesSheet } from './Sources';
import { MoreDetail } from './Detail';
import type { Daily } from '../../season';
import Icon from '../Icons';
import { useEffect, useState } from 'react';
import { AboutField, Actions, EventLog, ProvList, acres, coords, county, cropName, fieldCode, fieldName, latestCrop, place, type Step } from './shared';
import { FirstNationsCard } from './FirstNations';
import { FieldNow, LastSeasons, whenT, type LoadState } from './FieldNow';
import { MONTHS, TODAY_T } from '../../lib';

export interface FieldPanelProps {
  loc: Location; prov: ProvMap; cal: Calendar | null; regional: Regional | null; regionalLive: RegionalLive; strategies: RotationStrategy[] | null; allocation?: number; exampleLimit: boolean; daily: Daily | null;
  nasa: NasaDataset[] | null; nasaNow: NasaNow | null; extras: Extras; iss: { photo: ISSPhoto; credit: string } | null; dataState: LoadState; dailyState: LoadState;
  t: number; setT: (t: number) => void; events: FieldEvent[];
  onStep: (s: Step) => void; onClose: () => void;
}

export function FieldPanel(p: FieldPanelProps) {
  const { loc } = p;
  const thumbs = useThumbs();
  const [src, setSrc] = useState(false);
  const [snap, setSnap] = useState<'peek' | 'half' | 'full'>('half'); // phone bottom sheet height
  const now = latestCrop(loc);
  const isToday = p.t === TODAY_T;
  return (
    <section className={`panel fpanel sheet-${snap}`} data-testid="field-panel">
      <button className="fp-grab" onClick={() => setSnap(snap === 'peek' ? 'half' : snap === 'half' ? 'full' : 'peek')} aria-label="Resize the field panel" data-testid="grab"><i /></button>
      <header className="fp-head">
        <div className="fp-title">
          <h1>{fieldName(loc)}</h1>
          <button className="sq-btn" onClick={p.onClose} title="Close"><Icon name="close" size={16} /></button>
        </div>
        <p className="fp-facts"><b>{acres(loc)} acres</b>, {now.crop.toLowerCase()} in {now.year}, {place(loc)}</p>
        <p className="fp-id">{isBC(loc) ? 'British Columbia' : fieldCode(loc).replace('DWR ', 'State field no. ')}, {coords(loc)}</p>
      </header>
      <div className="panel-scroll">
        <h2 className="fp-h">{isToday ? 'Your field now' : 'Your field in ' + whenT(p.t)}{!isToday && <small><button className="link" onClick={() => p.setT(TODAY_T)}>Back to today</button></small>}</h2>
        <FieldNow dataState={p.dataState} dailyState={p.dailyState} thumb={thumbs?.[loc.id] ?? null} extras={p.extras} nasaNow={p.nasaNow} loc={loc} cal={p.cal} regional={p.regional} regionalLive={p.regionalLive} strategies={p.strategies} allocation={p.allocation} exampleLimit={p.exampleLimit} t={p.t} daily={p.daily} prov={p.prov} />
        {isBC(loc) && <FirstNationsCard loc={loc} />}
        <MoreDetail what="Sources, past seasons, 3D" />
        <div className="d-only">
        <h2 className="fp-h" data-testid="nasa-section">NASA data behind this field</h2>
        <ISSFigure iss={p.iss} />
        {p.nasa ? <NasaList list={p.nasa} /> : <p className="muted">Loading…</p>}
        <h2 className="fp-h">About the ground<small><button className="link" onClick={() => p.onStep('drill')} data-testid="step-drill">Look under the field in 3D: crop, soil moisture, groundwater</button></small></h2>
        <AboutField loc={loc} prov={p.prov} cal={p.cal} insurance={p.extras.insurance ?? loc.rma ?? null} insGap={bcGap(loc, 'insurance')} />
        <h2 className="fp-h">The last 3 seasons</h2>
        <LastSeasons loc={loc} cal={p.cal} t={p.t} />
        {p.events.length > 0 && <><h2 className="fp-h">What happened around here<small>Click one to move the timeline.</small></h2><EventLog events={p.events} setT={p.setT} /></>}
        <button className="link sources-link" onClick={() => setSrc(true)} data-testid="sources-link">Sources</button>
        {src && <SourcesSheet bc={isBC(loc)} onClose={() => setSrc(false)} />}
        </div>
        <p className="footnote">CropLytics helps the grower and adviser decide; it does not replace either.</p>
      </div>
      <footer className="fp-foot"><Actions onStep={p.onStep} /></footer>
    </section>
  );
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
        {p.onClose && <button className="pk-close" onClick={p.onClose} title="Close"><Icon name="close" size={16} /></button>}
      </header>
      {p.locations.length > 1 && (
        <div className="pk-filter">
          <label className="pk-search"><Icon name="search" size={16} /><input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by town, county or crop" aria-label="Search fields" data-testid="pk-search" /></label>
          <div className="pk-chips" role="group" aria-label="Crop">
            {fams.map(({ f, label, n }) => <button key={f} className={fam === f ? 'on' : ''} aria-pressed={fam === f} onClick={() => setFam(fam === f ? null : f)} data-testid={`chip-${f}`}>{label} <small>{n}</small></button>)}
          </div>
        </div>
      )}
      {p.live === false && <p className="offline-note" data-testid="offline-note">The CropLytics server is not answering, so every number is an example. Start the API (see the README) and reload for real data.</p>}
      {p.locations.length === 0 && <p className="loading-note">Loading the fields…</p>}
      {([['ca', shownCA], ['bc', shownBC]] as const).map(([rg, rows]) => rows.length > 0 && (
      <div key={rg}>
      {rg === 'bc' && <h2 className="pk-group" data-testid="pk-group-bc">British Columbia</h2>}
      <ul className="pk-list" data-testid={rg === 'bc' ? 'field-table-bc' : 'field-table'}>
        {rows.map((l) => {
          const now = latestCrop(l), th = thumbs?.[l.id], strip = p.strips[l.id];
          return (
            <li key={l.id}>
              <button className={`pk-row ${p.selectedId === l.id ? 'on' : ''}`} onClick={() => p.onSelect(l.id)} data-testid={`row-${l.id}`}>
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
      {p.locations.length > 0 && !shown.length && <p className="loading-note">No field matches. <button className="link" onClick={() => { setQ(''); setFam(null); }}>Show all</button></p>}
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
