// Core field panel: decision on the left, meters in the bottom dock.
import type { Calendar, FieldEvent, Location, NewsItem, Regional, RotationStrategy } from '../../types';
import type { Extras, ISSPhoto, NasaNow, ProvMap, RegionalLive } from '../../api';
import type { NasaDataset } from '../../nasa';
import type { Daily } from '../../season';
import Icon from '../Icons';
import { useEffect, useState } from 'react';
import { StepHead, acres, fieldName, isBC, latestCrop, placeLabel, type Step } from './shared';
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
      <StepHead id="now" title="Your field now" purpose="Check whether what you grow today fits the water you have. The next steps build on this." />
      <div className="panel-scroll">
        <p className="step-field"><b>{fieldName(loc)}</b><span>{acres(loc)} acres · {now.crop.toLowerCase()} in {now.year}</span></p>
        <p className="talk-q">{isToday ? 'Will today’s plan fit your water?' : `What about ${whenT(p.t)}?`}
          {!isToday && <button className="link" onClick={() => p.setT(TODAY_T)}>Back to today</button>}
        </p>
        <FieldNow {...shared} mode="takeaway" />
      </div>
      <footer className="step-foot">
        <button className="next-step" onClick={() => p.onStep('season')} data-testid="now-to-season">
          <span><b>Next: coming season</b><small>Winter rain and whether next year still fits</small></span>
          <Icon name="right" size={18} />
        </button>
      </footer>
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
      <StepHead id="pick" title="Pick your field" purpose="Choose the field you want to plan. Everything after this is about that field." />
      {p.live === false && <p className="offline-note" data-testid="offline-note"><i className="ex-hatch" />Example numbers. The server is not answering.</p>}
      {p.locations.length === 0 && <p className="loading-note">Finding fields…</p>}
      <ul className="pk-list" data-testid="field-table">
        {p.locations.map((l) => {
          const now = latestCrop(l), th = thumbs?.[l.id];
          return (
            <li key={l.id}>
              <button className={`pk-card ${p.selectedId === l.id ? 'on' : ''}`} onClick={() => p.onSelect(l.id)} data-testid={`row-${l.id}`}>
                <span className="pk-thumb">
                  <img src={`${import.meta.env.BASE_URL}thumbs/${l.id}.jpg`} alt={`Satellite view of ${fieldName(l)}`} />
                  {th && <svg viewBox="0 0 360 240" preserveAspectRatio="none" aria-hidden="true"><polygon points={outlinePts(l, th.bbox)} /></svg>}
                </span>
                <span className="pk-body">
                  <b>{fieldName(l)}</b>
                  <span className="pk-facts">{acres(l)} acres · {now.crop.toLowerCase()} in {now.year}</span>
                  <span className="pk-place">{placeLabel(l)}</span>
                </span>
                <span className="pk-cta">{p.selectedId === l.id ? 'Continue with this field' : 'Pick this field'}<Icon name="right" size={18} /></span>
              </button>
            </li>
          );
        })}
      </ul>
      <p className="pk-or">Or tap the field’s pin on the map.</p>
      {p.locations.some(isBC) && (
        <details className="pk-more" data-testid="pk-more">
          <summary>About this area <small>optional reading</small></summary>
          <div className="pk-fn">
            <FirstNationsCard loc={p.locations.find(isBC)!} />
          </div>
        </details>
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
