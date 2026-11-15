// Core field panel: decision on the left, meters in the bottom dock.
import type { Calendar, FieldEvent, Location, NewsItem, Regional, RotationStrategy } from '../../types';
import type { Extras, ISSPhoto, NasaNow, ProvMap, RegionalLive } from '../../api';
import type { NasaDataset } from '../../nasa';
import type { Daily } from '../../season';
import Icon from '../Icons';
import { useEffect, useState } from 'react';
import { Workflow, acres, fieldName, isBC, latestCrop, placeLabel, type Step } from './shared';
import { FieldNow, whenT, type LoadState } from './FieldNow';
import { FirstNationsCard } from './FirstNations';
import { DockBottom } from './Dock';
import { TODAY_T } from '../../lib';

export interface FieldPanelProps {
  loc: Location; prov: ProvMap; cal: Calendar | null; regional: Regional | null; regionalLive: RegionalLive; strategies: RotationStrategy[] | null; allocation?: number; exampleLimit: boolean; daily: Daily | null;
  nasa: NasaDataset[] | null; nasaNow: NasaNow | null; extras: Extras; iss: { photo: ISSPhoto; credit: string } | null; news: NewsItem[]; dataState: LoadState; dailyState: LoadState;
  t: number; setT: (t: number) => void; events: FieldEvent[];
  onStep: (s: Step) => void; onClose: () => void;
}

export function FieldPanel(p: FieldPanelProps) {
  const { loc } = p;
  const thumbs = useThumbs();
  const now = latestCrop(loc);
  const isToday = p.t === TODAY_T;
  const shared = {
    dataState: p.dataState, dailyState: p.dailyState, thumb: thumbs?.[loc.id] ?? null, extras: p.extras, nasaNow: p.nasaNow, loc, cal: p.cal, regional: p.regional, regionalLive: p.regionalLive, strategies: p.strategies, allocation: p.allocation, exampleLimit: p.exampleLimit, t: p.t, daily: p.daily, prov: p.prov,
  };
  return (
    <section className="panel fpanel docked talk" data-testid="field-panel">
      <header className="fp-head">
        <div className="fp-title"><h1>{fieldName(loc)}</h1></div>
        <p className="fp-facts"><b>{acres(loc)} acres</b> · {now.crop.toLowerCase()} in {now.year}</p>
      </header>
      <div className="panel-scroll">
        <p className="talk-q">{isToday ? 'Will today’s plan fit your water?' : `What about ${whenT(p.t)}?`}
          {!isToday && <button className="link" onClick={() => p.setT(TODAY_T)}>Today</button>}
        </p>
        <FieldNow {...shared} mode="takeaway" />
        <button className="btn primary wide now-next" onClick={() => p.onStep('season')} data-testid="now-to-season">Next: season<Icon name="right" size={16} /></button>
      </div>
      <DockBottom>
        <div className="bottom-inner">
          <p className="bottom-label">At a glance</p>
          <FieldNow {...shared} mode="glance" />
        </div>
      </DockBottom>
    </section>
  );
}

export function FieldPicker(p: { locations: Location[]; live: boolean | null; strips: Record<string, Record<number, string>>; selectedId: string | null; onSelect: (id: string) => void; onBC: () => void; onClose?: () => void }) {
  const thumbs = useThumbs();
  return (
    <section className="picker2 docked talk" data-testid="fields-panel">
      <header className="pk-head">
        <h1>Which field?</h1>
        <Workflow current="pick" problem hideSteps />
      </header>
      {p.live === false && <p className="offline-note" data-testid="offline-note">Server offline — example numbers.</p>}
      {p.locations.length === 0 && <p className="loading-note">Finding fields…</p>}
      <ul className="pk-list" data-testid="field-table">
        {p.locations.map((l) => {
          const now = latestCrop(l), th = thumbs?.[l.id];
          return (
            <li key={l.id}>
              <button className={`pk-row ${p.selectedId === l.id ? 'on' : ''}`} onClick={() => p.onSelect(l.id)} data-testid={`row-${l.id}`}>
                <span className="pk-thumb">
                  <img src={`${import.meta.env.BASE_URL}thumbs/${l.id}.jpg`} alt={`Satellite view of ${fieldName(l)}`} />
                  {th && <svg viewBox="0 0 360 240" preserveAspectRatio="none" aria-hidden="true"><polygon points={outlinePts(l, th.bbox)} /></svg>}
                </span>
                <span className="pk-body">
                  <b>{fieldName(l)}</b>
                  <span className="pk-facts">{placeLabel(l)} · {acres(l)} acres · {now.crop.toLowerCase()} in {now.year}</span>
                  {isBC(l) && <span className="pk-tag">BC Salmon River · near First Nations lands</span>}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      {p.locations.some(isBC) && (
        <div className="pk-fn">
          <FirstNationsCard loc={p.locations.find(isBC)!} />
        </div>
      )}
    </section>
  );
}

function outlinePts(l: Location, b: number[]) {
  return l.geometry.coordinates[0].map(([x, y]) => `${(((x - b[0]) / (b[2] - b[0])) * 360).toFixed(1)},${(((b[3] - y) / (b[3] - b[1])) * 240).toFixed(1)}`).join(' ');
}

let thumbsP: Promise<Record<string, { bbox: number[] }> | null> | null = null;
function useThumbs() {
  const [t, setT] = useState<Record<string, { bbox: number[] }> | null>(null);
  useEffect(() => { (thumbsP ??= fetch(`${import.meta.env.BASE_URL}thumbs/thumbs.json`).then((r) => r.json()).then((j) => j.fields).catch(() => ({}))).then(setT); }, []);
  return t;
}
