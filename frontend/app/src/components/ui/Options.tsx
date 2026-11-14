// One farmer-first field panel. Order: what this field is -> "Your field now" answers -> about the ground -> last 3 seasons -> sources.
// The next steps sit in a fixed footer so they are always visible without scrolling.
import type { Calendar, FieldEvent, Location, Regional, RotationStrategy } from '../../types';
import type { ISSPhoto, NasaNow, ProvMap, RegionalLive } from '../../api';
import type { NasaDataset } from '../../nasa';
import { ISSFigure, NasaList } from './NasaSection';
import type { Daily } from '../../season';
import Icon from '../Icons';
import { AboutField, Actions, CROP_COL, EventLog, ProvList, acres, coords, county, fieldCode, fieldName, latestCrop, mainCrop, nearTown, recordLine, type Step } from './shared';
import { FieldNow, LastSeasons, whenT } from './FieldNow';
import { TODAY_T } from '../../lib';

export interface FieldPanelProps {
  loc: Location; prov: ProvMap; cal: Calendar | null; regional: Regional | null; regionalLive: RegionalLive; strategies: RotationStrategy[] | null; allocation?: number; exampleLimit: boolean; daily: Daily | null;
  nasa: NasaDataset[] | null; nasaNow: NasaNow | null; iss: { photo: ISSPhoto; credit: string } | null; loading: boolean;
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
        {p.loading && <p className="loading-note" data-testid="field-loading">Loading this field’s satellite, weather and water data…</p>}
        <FieldNow nasaNow={p.nasaNow} loc={loc} cal={p.cal} regional={p.regional} regionalLive={p.regionalLive} strategies={p.strategies} allocation={p.allocation} exampleLimit={p.exampleLimit} t={p.t} daily={p.daily} prov={p.prov} />
        <h2 className="fp-h" data-testid="nasa-section">NASA data behind this field<small>What each one tells you, how coarse it is, and whether it is live.</small></h2>
        <ISSFigure iss={p.iss} />
        {p.nasa ? <NasaList list={p.nasa} /> : <p className="muted">Loading…</p>}
        <h2 className="fp-h">About the ground<small><button className="link" onClick={() => p.onStep('drill')} data-testid="step-drill">Look under the field in 3D: crop, soil moisture, groundwater</button></small></h2>
        <AboutField loc={loc} prov={p.prov} cal={p.cal} />
        <h2 className="fp-h">The last 3 seasons</h2>
        <LastSeasons loc={loc} cal={p.cal} t={p.t} />
        {p.events.length > 0 && <><h2 className="fp-h">What happened around here<small>Click one to move the timeline.</small></h2><EventLog events={p.events} setT={p.setT} /></>}
        <details className="prov"><summary>Where every number comes from</summary><ProvList prov={p.prov} /></details>
        <p className="footnote">CropLytics helps the grower and adviser decide; it does not replace either.</p>
      </div>
      <footer className="fp-foot"><Actions onStep={p.onStep} /></footer>
    </section>
  );
}

/** "Pick your field": the overview list, in the words a grower would use. */
export function FieldPicker(p: { locations: Location[]; live: boolean | null; selectedId: string | null; onSelect: (id: string) => void; onBC: () => void; onClose?: () => void }) {
  return (
    <section className="panel fpanel picker" data-testid="fields-panel">
      <header className="fp-head">
        <div className="fp-title"><h1>Pick your field</h1>{p.onClose && <button className="sq-btn" onClick={p.onClose} title="Close"><Icon name="close" size={16} /></button>}</div>
        <p className="fp-facts">See what is happening on it now, what this winter is likely to bring, and what a different rotation would cost in water.</p>
      </header>
      <div className="panel-scroll">
        {p.live === false && <p className="offline-note" data-testid="offline-note">The CropLytics server is not answering, so every number below is an example. Start the API (see the README) and reload for real data.</p>}
        {p.locations.length === 0 ? <p className="loading-note">Loading the fields…</p> : <p className="muted pick-note">Two California fields are set up so far. Choose one, or click its outline on the map.</p>}
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
                    <small>{recordLine(l)}</small>
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
