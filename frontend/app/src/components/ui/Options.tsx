// One farmer-first field panel (replaces the ?ui=1|2|3 dossier / mission strip / analysis rail options).
// Order: what this field is -> plain answers about it right now -> what you can do next -> details -> sources.
import type { Calendar, FieldEvent, Location, Regional, RotationStrategy } from '../../types';
import type { ProvMap } from '../../api';
import Icon from '../Icons';
import { AboutField, Actions, CROP_COL, Answers, CropRecord, EventLog, ProvList, acres, coords, county, fieldCode, fieldName, latestCrop, mainCrop, nearTown, yearLabel, type Step } from './shared';

export interface FieldPanelProps {
  loc: Location; prov: ProvMap; cal: Calendar | null; regional: Regional | null; strategies: RotationStrategy[] | null; allocation?: number;
  t: number; setT: (t: number) => void; detector: 'rule' | 'ml'; events: FieldEvent[];
  onStep: (s: Step) => void; onClose: () => void;
}

export function FieldPanel(p: FieldPanelProps) {
  const { loc } = p;
  const now = latestCrop(loc);
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
        <h2 className="fp-h">This field in {yearLabel(p.t)}<small>Drag the timeline at the bottom to change the date.</small></h2>
        <Answers loc={loc} cal={p.cal} regional={p.regional} strategies={p.strategies} allocation={p.allocation} t={p.t} detector={p.detector} prov={p.prov} />
        <h2 className="fp-h">What you can do next</h2>
        <Actions onStep={p.onStep} />
        <h2 className="fp-h">About this field</h2>
        <AboutField loc={loc} prov={p.prov} />
        <h2 className="fp-h">Crops grown here</h2>
        <CropRecord loc={loc} prov={p.prov} />
        {p.events.length > 0 && <><h2 className="fp-h">What happened here<small>Click one to move the timeline.</small></h2><EventLog events={p.events} setT={p.setT} /></>}
        <details className="prov"><summary>Where every number comes from</summary><ProvList prov={p.prov} /></details>
        <p className="footnote">Field Shift helps the grower and adviser decide; it does not replace either.</p>
      </div>
    </section>
  );
}

/** "Pick your field": the overview list, in the words a grower would use. */
export function FieldPicker(p: { locations: Location[]; selectedId: string | null; onSelect: (id: string) => void; onBC: () => void; onClose?: () => void }) {
  return (
    <section className="panel fpanel picker" data-testid="fields-panel">
      <header className="fp-head">
        <div className="fp-title"><h1>Pick your field</h1>{p.onClose && <button className="sq-btn" onClick={p.onClose} title="Close"><Icon name="close" size={16} /></button>}</div>
        <p className="fp-facts">Two California fields are set up so far. Choose one, or click its outline on the map.</p>
      </header>
      <div className="panel-scroll">
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
                    <small>{l.headline} {l.dwr_id ? `State field no. ${l.dwr_id}.` : ''}</small>
                  </span>
                  <Icon name="right" size={16} />
                </button>
              </li>
            );
          })}
          <li>
            <button className="dim" onClick={p.onBC}>
              <i className="pick-sw none" />
              <span><b>Sumas Prairie, British Columbia</b><span className="pick-facts">Not set up yet</span><small>Why it is not modelled, and what it would take.</small></span>
              <Icon name="right" size={16} />
            </button>
          </li>
        </ul>
      </div>
    </section>
  );
}
