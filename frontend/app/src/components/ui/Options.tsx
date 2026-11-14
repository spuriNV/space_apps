// The three selection / field-panel options, switched with ?ui=1|2|3.
import type { Calendar, FieldEvent, Location, Regional } from '../../types';
import type { ProvMap } from '../../api';
import Icon from '../Icons';
import { CropRecord, EventLog, FieldTable, ProvList, Readouts, SiteFacts, SoilBlock, Src, Workflow, county, coords, fieldCode, type Step } from './shared';

export interface FieldPanelProps {
  locations: Location[]; loc: Location | null; selectedId: string | null; prov: ProvMap; cal: Calendar | null; regional: Regional | null;
  t: number; setT: (t: number) => void; detector: 'rule' | 'ml'; events: FieldEvent[];
  onSelect: (id: string) => void; onBC: () => void; onStep: (s: Step) => void; onClose: () => void;
}

// ---------- 1. Field dossier: left instrument sheet ----------
export function Dossier(p: FieldPanelProps & { loc: Location }) {
  const { loc } = p;
  return (
    <section className="panel glass dossier" data-testid="field-panel">
      <header className="dz-head">
        <div className="dz-eyebrow"><span>Field dossier</span><span>{county(loc)} County · California</span></div>
        <div className="dz-title">
          <h1 className="mono">{fieldCode(loc)}</h1>
          <button className="sq-btn" onClick={p.onClose} title="Close dossier"><Icon name="close" size={16} /></button>
        </div>
        <p>{loc.short_name} <span className="dim">· {coords(loc)}</span></p>
        <p className="dz-brief">{loc.headline}</p>
      </header>
      <div className="panel-scroll">
        <Readouts cal={p.cal} regional={p.regional} t={p.t} detector={p.detector} prov={p.prov} />
        <div className="sec-h"><span>Planning steps</span><small>grower and adviser</small></div>
        <Workflow onStep={p.onStep} />
        <div className="sec-h"><span>Site</span></div>
        <SiteFacts loc={loc} prov={p.prov} />
        <SoilBlock loc={loc} prov={p.prov} />
        <CropRecord loc={loc} prov={p.prov} />
        <EventLog events={p.events} setT={p.setT} />
        <details className="prov"><summary>Where each number comes from</summary><ProvList prov={p.prov} /></details>
        <p className="footnote">Supports the grower’s and adviser’s judgement; it does not replace either.</p>
      </div>
    </section>
  );
}

export function FieldsSheet(p: { locations: Location[]; selectedId: string | null; onSelect: (id: string) => void; onBC: () => void; onClose: () => void }) {
  return (
    <section className="panel glass dossier" data-testid="fields-panel">
      <header className="dz-head">
        <div className="dz-eyebrow"><span>Field register</span><span>California</span></div>
        <div className="dz-title"><h1>Pick a field</h1><button className="sq-btn" onClick={p.onClose}><Icon name="close" size={16} /></button></div>
      </header>
      <div className="panel-scroll">
        <FieldTable locations={p.locations} selectedId={p.selectedId} onSelect={p.onSelect} onBC={p.onBC} />
        <p className="muted pad">Two example fields with rich ground data, chosen from DWR 2023 field outlines and checked against the Cropland Data Layer. Click an outline on the map to open its dossier.</p>
      </div>
    </section>
  );
}

// ---------- 2. Mission strip: bottom console with field tabs ----------
export function MissionStrip(p: FieldPanelProps) {
  const loc = p.loc;
  return (
    <section className={`mstrip glass ${loc ? 'open' : ''}`} data-testid="field-panel">
      <nav className="ms-tabs">
        {p.locations.map((l) => (
          <button key={l.id} className={p.selectedId === l.id ? 'on' : ''} onClick={() => (p.selectedId === l.id ? p.onClose() : p.onSelect(l.id))} data-testid={`tab-${l.id}`}>
            <i className="ms-led" /><b className="mono">{fieldCode(l)}</b><span>{l.short_name}</span>
          </button>
        ))}
        <button className="ms-bc" onClick={p.onBC}><i className="ms-led off" /><b className="mono">BC</b><span>not modelled</span></button>
        <span className="ms-fill" />
        {loc ? <span className="ms-meta mono">{coords(loc)}</span> : <span className="ms-meta">Select a field tab or click an outline on the map</span>}
      </nav>
      {loc && (
        <div className="ms-body">
          <div className="ms-col">
            <div className="sec-h"><span>Site</span><small>{county(loc)} County</small></div>
            <SiteFacts loc={loc} prov={p.prov} />
          </div>
          <div className="ms-col"><Readouts cal={p.cal} regional={p.regional} t={p.t} detector={p.detector} prov={p.prov} compact /></div>
          <div className="ms-col"><SoilBlock loc={loc} prov={p.prov} /></div>
          <div className="ms-col"><CropRecord loc={loc} prov={p.prov} from={2014} /></div>
          <div className="ms-col steps">
            <div className="sec-h"><span>Next</span></div>
            <Workflow onStep={p.onStep} />
          </div>
        </div>
      )}
    </section>
  );
}

// ---------- 3. Split analysis: map dominant, fixed data rail ----------
export function AnalysisRail(p: FieldPanelProps) {
  const loc = p.loc;
  return (
    <aside className="arail" data-testid="field-panel">
      <header className="ar-head"><span className="mono">Analysis</span><small>{loc ? `${fieldCode(loc)} · ${loc.short_name}` : 'no field selected'}</small>
        {loc && <button className="sq-btn" onClick={p.onClose} title="Clear selection"><Icon name="close" size={14} /></button>}</header>
      <div className="ar-scroll">
        <section><h3><em>A</em>Fields in this study</h3><FieldTable locations={p.locations} selectedId={p.selectedId} onSelect={p.onSelect} onBC={p.onBC} /></section>
        {!loc && <p className="ar-empty">Select a row or click a field outline. The rail then fills with the field’s readouts, soil, crop record and the planning steps. Map stays in control: scroll in on a field to separate surface, soil and groundwater layers.</p>}
        {loc && (
          <>
            <section><h3><em>B</em>Readouts at the timeline date</h3><Readouts cal={p.cal} regional={p.regional} t={p.t} detector={p.detector} prov={p.prov} /></section>
            <section><h3><em>C</em>Site</h3><SiteFacts loc={loc} prov={p.prov} /></section>
            <section><h3><em>D</em>Soil and record</h3><SoilBlock loc={loc} prov={p.prov} /><CropRecord loc={loc} prov={p.prov} /></section>
            <section><h3><em>E</em>Planning steps</h3><Workflow onStep={p.onStep} /></section>
            <section><h3><em>F</em>Events</h3><EventLog events={p.events} setT={p.setT} /></section>
            <section><h3><em>G</em>Provenance <Src p={p.prov.strategies} /></h3><ProvList prov={p.prov} /></section>
          </>
        )}
      </div>
    </aside>
  );
}
