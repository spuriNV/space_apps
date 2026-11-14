// One farmer-first field panel. Order: what this field is -> "Your field now" answers -> about the ground -> last 3 seasons -> sources.
// The next steps sit in a fixed footer so they are always visible without scrolling.
import type { Calendar, FieldEvent, Location, Regional, RotationStrategy } from '../../types';
import type { ProvMap } from '../../api';
import type { Daily } from '../../season';
import Icon from '../Icons';
import { AboutField, Actions, CROP_COL, EventLog, ProvList, acres, coords, county, fieldCode, fieldName, latestCrop, mainCrop, nearTown, type Step } from './shared';
import { FieldNow, LastSeasons, whenT } from './FieldNow';
import { TODAY_T } from '../../lib';

export interface FieldPanelProps {
  loc: Location; prov: ProvMap; cal: Calendar | null; regional: Regional | null; strategies: RotationStrategy[] | null; allocation?: number; daily: Daily | null;
  t: number; setT: (t: number) => void; events: FieldEvent[];
  onStep: (s: Step) => void; onClose: () => void;
}

export function FieldPanel(p: FieldPanelProps) {
  const { loc } = p;
  const now = latestCrop(loc);
  const isToday = p.t === TODAY_T;
  return (
    <section className="panel fpanel" data-testid="field-panel">
      <header className="fp-head">
        <div className="fp-title">
          <h1>{fieldName(loc)}</h1>
          <button className="sq-btn" onClick={p.onClose} title="Close"><Icon name="close" size={16} /></button>
        </div>
        <p className="fp-facts"><b>{acres(loc)} acres</b>, {now.crop.toLowerCase()} in {now.year}, {county(loc)} County</p>
        <p className="fp-id">{fieldCode(loc).replace('DWR ', 'State field no. ')}, {coords(loc)}</p>
      </header>
      <div className="panel-scroll">
        <h2 className="fp-h">{isToday ? 'Your field now' : 'Your field in ' + whenT(p.t)}<small>{isToday ? `Today, ${whenT(p.t)}. Drag the timeline to look back.` : <button className="link" onClick={() => p.setT(TODAY_T)}>Back to today</button>}</small></h2>
        <FieldNow loc={loc} cal={p.cal} regional={p.regional} strategies={p.strategies} allocation={p.allocation} t={p.t} daily={p.daily} prov={p.prov} />
        <h2 className="fp-h">About the ground<small><button className="link" onClick={() => p.onStep('drill')} data-testid="step-drill">Look under the field in 3D: crop, soil moisture, groundwater</button></small></h2>
        <AboutField loc={loc} prov={p.prov} />
        <h2 className="fp-h">The last 3 seasons</h2>
        <LastSeasons loc={loc} cal={p.cal} t={p.t} />
        {p.events.length > 0 && <><h2 className="fp-h">What happened around here<small>Click one to move the timeline.</small></h2><EventLog events={p.events} setT={p.setT} /></>}
        <details className="prov"><summary>Where every number comes from</summary><ProvList prov={p.prov} /></details>
        <p className="footnote">Field Shift helps the grower and adviser decide; it does not replace either.</p>
      </div>
      <footer className="fp-foot"><Actions onStep={p.onStep} /></footer>
    </section>
  );
}

/** "Pick your field": the overview list, in the words a grower would use. */
export function FieldPicker(p: { locations: Location[]; selectedId: string | null; onSelect: (id: string) => void; onBC: () => void; onClose?: () => void }) {
  return (
    <section className="panel fpanel picker" data-testid="fields-panel">
      <header className="fp-head">
        <div className="fp-title"><h1>Pick your field</h1>{p.onClose && <button className="sq-btn" onClick={p.onClose} title="Close"><Icon name="close" size={16} /></button>}</div>
        <p className="fp-facts">See what is happening on it now, what this winter is likely to bring, and what a different rotation would cost in water.</p>
      </header>
      <div className="panel-scroll">
        <p className="muted pick-note">Two California fields are set up so far. Choose one, or click its outline on the map.</p>
        <ul className="picklist" data-testid="field-table">
          {p.locations.map((l) => {
            const now = latestCrop(l);
            return (
              <li key={l.id}>
                <button className={p.selectedId === l.id ? 'on' : ''} onClick={() => p.onSelect(l.id)} data-testid={`row-${l.id}`}>
                  <i className="pick-sw" style={{ background: CROP_COL(mainCrop(l)) }} />
                  <span>
                    <b>{mainCrop(l)} field {nearTown(l)}</b>
                    <span className="pick-facts">{county(l)} County, {acres(l)} acres, {now.crop.toLowerCase()} in {now.year}</span>
                    <small>{l.headline}</small>
                  </span>
                  <Icon name="right" size={16} />
                </button>
              </li>
            );
          })}
          <li>
            <button className="dim" onClick={p.onBC}>
              <i className="pick-sw none" />
              <span><b>Sumas Prairie, British Columbia</b><span className="pick-facts">Not set up yet</span><small>Why not yet, and what it would take.</small></span>
              <Icon name="right" size={16} />
            </button>
          </li>
        </ul>
      </div>
    </section>
  );
}
