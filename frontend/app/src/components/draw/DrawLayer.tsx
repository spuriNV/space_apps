// "Draw a field": the pill on the map, the drawing bar (Rectangle / Shape / Cancel, live acres, handles to reshape), the name
// dialog, the delete and "add this shared field" dialogs. App owns the list of fields (useMyFields); this component owns
// the drawing session and tells App when it starts, when a field is being saved and when it is saved.
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';
import type maplibregl from 'maplibre-gl';
import './draw.css';
import Icon from '../Icons';
import { Seg } from '../ui/Seg';
import { Modal } from './Modal';
import type { DrawHandle, DrawKind } from './terraDraw';
import { DRAFT_ID, nextName, openRing, ringAcres, type MyFields, type Polygon, type Submit } from '../../myFields';
import { acres as acresOf, county } from '../ui/shared';
import type { Location } from '../../types';

export interface DrawHostHandle { start: () => void; redraw: (loc: Location) => void; rename: (loc: Location) => void; del: (loc: Location) => void }
interface Props {
  getMap: () => maplibregl.Map | null;
  mf: MyFields;
  rightInset: number;
  /** a drawing session began or ended; `hideId` is a field whose outline the map should not draw while it is redrawn */
  onActive: (on: boolean, hideId?: string | null) => void;
  /** a save started: show the field panel now (the draft stand-in, in its skeleton state) */
  onSubmitting: () => void;
  /** the save ended: the new id, or null when it failed (the panel shows the error) */
  onSaved: (id: string | null) => void;
  onDeleted: (id: string) => void;
  /** a shared field was added or already yours: open it */
  onOpenShared: (id: string) => void;
}
type Phase = 'off' | 'draw' | 'edit';
type Dlg = { t: 'name'; mode: 'new' | 'rename'; geometry: Polygon; loc?: Location } | { t: 'delete'; loc: Location };
const MIN_AC = 1.24, MAX_AC = 4942; // 0.5 ha and 2,000 ha: the API's limits, shown as hints while drawing
const phoneNow = () => window.matchMedia('(max-width: 640px)').matches;
const fmtAc = (a: number) => (a < 10 ? a.toFixed(1) : Math.round(a).toLocaleString('en-US'));

export const DrawLayer = forwardRef<DrawHostHandle, Props>(function DrawLayer(p, ref) {
  const { mf } = p;
  const [phase, setPhase] = useState<Phase>('off');
  const [kind, setKind] = useState<DrawKind>('rect');
  const [acres, setAcres] = useState<number | null>(null);
  const [redraw, setRedraw] = useState<{ name: string; replaceId?: string } | null>(null);
  const [dlg, setDlg] = useState<Dlg | null>(null);
  const draw = useRef<DrawHandle | null>(null);
  const token = useRef(0);
  const live = useRef(p);
  live.current = p;

  const begin = async (k: DrawKind, load?: Polygon) => {
    const map = live.current.getMap();
    if (!map) return;
    const my = ++token.current;
    const mod = await import('./terraDraw');
    if (my !== token.current) return;
    draw.current?.destroy();
    try {
      draw.current = mod.createDraw(map, {
        onRing: (r) => { const o = r ? openRing(r) : []; setAcres(o.length >= 3 ? ringAcres(o) : null); },
        onFinished: () => setPhase('edit'),
      });
      if (load) draw.current.load(load); else draw.current.mode(k);
    } catch { setPhase('off'); live.current.onActive(false); }
  };
  const end = () => { token.current++; draw.current?.destroy(); draw.current = null; setPhase('off'); setAcres(null); setRedraw(null); setDlg(null); };
  const cancel = () => { end(); p.onActive(false); };
  useEffect(() => () => { token.current++; draw.current?.destroy(); }, []);

  const save = (a: Submit) => { end(); p.onActive(false); p.onSubmitting(); mf.submit(a).then(p.onSaved); };
  const start = () => {
    const k: DrawKind = phoneNow() ? 'shape' : 'rect';
    setKind(k); setPhase('draw'); setAcres(null); setRedraw(null); p.onActive(true); begin(k);
  };
  useImperativeHandle(ref, () => ({
    start,
    redraw(loc) {
      const replaceId = loc.id === DRAFT_ID ? mf.draft?.args.replaceId : loc.id;
      if (loc.id === DRAFT_ID) mf.dropDraft();
      setRedraw({ name: loc.mine?.name ?? 'My field', replaceId }); setPhase('edit'); setAcres(null);
      p.onActive(true, replaceId ?? null);
      begin(kind, loc.geometry);
    },
    rename(loc) { setDlg({ t: 'name', mode: 'rename', geometry: loc.geometry, loc }); },
    del(loc) { setDlg({ t: 'delete', loc }); },
  }));

  // Esc cancels a drawing in progress (a dialog handles its own Esc)
  useEffect(() => {
    if (phase === 'off' || dlg) return;
    const k = (e: KeyboardEvent) => { if (e.key === 'Escape') cancel(); };
    window.addEventListener('keydown', k);
    return () => window.removeEventListener('keydown', k);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, dlg]);

  // a shared link that is already in this person's list opens straight away
  const sh = mf.shared;
  useEffect(() => { if (sh?.known && sh.loc) { mf.declineShared(); p.onOpenShared(sh.id); } /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [sh]);

  const next = () => {
    const g = draw.current?.polygon();
    if (!g) return;
    if (redraw) save({ name: redraw.name, geometry: g, replaceId: redraw.replaceId });
    else setDlg({ t: 'name', mode: 'new', geometry: g });
  };
  const hint = phase === 'edit' ? 'Drag a corner to reshape it. Drag a small dot to add a corner.'
    : kind === 'rect' ? 'Drag across the field, or tap two opposite corners.' : 'Tap each corner of the field. Tap the first point to finish.';
  const size = acres == null ? null : acres < MIN_AC ? `Too small: the smallest field is ${MIN_AC.toFixed(1)} acres.` : acres > MAX_AC ? 'Too big: the largest field is about 5,000 acres.' : null;

  return (
    <>
      {phase === 'off' && <button className="draw-btn" style={{ right: 16 + p.rightInset }} onClick={start} data-testid="draw-btn"><Icon name="draw" size={18} />Draw a field</button>}
      {phase !== 'off' && (
        <div className="draw-bar" role="region" aria-label="Draw a field" data-testid="draw-bar" style={{ '--right': `${p.rightInset}px` } as React.CSSProperties}>
          <div className="draw-top">
            <h2>{redraw ? `Redraw ${redraw.name}` : 'Draw a field'}</h2>
            {acres != null && <p className={`draw-acres ${size ? 'bad' : ''}`} aria-live="polite" data-testid="draw-acres"><b className="tnum">{fmtAc(acres)}</b> acres</p>}
          </div>
          <p className="draw-hint">{size ?? hint}</p>
          <div className="draw-row">
            {phase === 'draw' && !redraw
              ? <Seg label="Drawing tool" value={kind} onChange={(k) => { setKind(k); setAcres(null); draw.current?.mode(k); }} testid="draw-kind"
                  options={[{ v: 'rect', label: <><Icon name="rect" size={18} />Rectangle</>, testid: 'draw-rect' }, { v: 'shape', label: <><Icon name="shape" size={18} />Shape</>, testid: 'draw-shape' }]} />
              : <button className="btn btn-outline" onClick={() => { setPhase('draw'); setAcres(null); setRedraw(null); draw.current?.mode(kind); }} data-testid="draw-again">Start over</button>}
            <span className="draw-gap" />
            <button className="btn btn-outline" onClick={cancel} data-testid="draw-cancel">Cancel</button>
            {phase === 'edit' && <button className="btn btn-primary" onClick={next} data-testid="draw-next">{redraw ? 'Save shape' : 'Name it'}</button>}
          </div>
        </div>
      )}
      {dlg?.t === 'name' && <NameDialog dlg={dlg} names={mf.refs.map((r) => r.name)} acres={dlg.mode === 'new' ? acres : null}
        onClose={() => setDlg(null)}
        onSave={(name) => {
          if (dlg.mode === 'new') save({ name, geometry: dlg.geometry });
          else if (dlg.loc && name !== dlg.loc.mine?.name) { setDlg(null); p.onSubmitting(); mf.submit({ name, geometry: dlg.geometry, replaceId: dlg.loc.id }).then(p.onSaved); }
          else setDlg(null);
        }} />}
      {dlg?.t === 'delete' && (
        <Modal title={`Delete ${dlg.loc.mine?.name ?? 'this field'}?`} onClose={() => setDlg(null)} testid="delete-dialog">
          <p className="dlg-text">It leaves your list on this device. A share link you already sent still opens it.</p>
          <div className="dlg-row">
            <button className="btn btn-outline" onClick={() => setDlg(null)} data-autofocus>Keep it</button>
            <button className="btn btn-danger" onClick={() => { const id = dlg.loc.id; mf.remove(id); setDlg(null); p.onDeleted(id); }} data-testid="delete-confirm"><Icon name="trash" />Delete field</button>
          </div>
        </Modal>
      )}
      {sh && !sh.known && (
        <Modal title={sh.loc ? 'Add this field to yours?' : 'This link did not open'} onClose={mf.declineShared} testid="share-dialog">
          {sh.loc ? <>
            <p className="dlg-text"><b>{sh.loc.mine?.name}</b>, {acresOf(sh.loc)} acres{sh.loc.county_name ? `, ${county(sh.loc)} County` : ''}. Someone shared it with you.</p>
            <div className="dlg-row">
              <button className="btn btn-outline" onClick={mf.declineShared}>Not now</button>
              <button className="btn btn-primary" data-autofocus onClick={() => { const id = mf.acceptShared(); if (id) p.onOpenShared(id); }} data-testid="share-add">Add to my fields</button>
            </div>
          </> : <>
            <p className="dlg-text">{sh.error?.message ?? 'The field could not be opened.'}</p>
            <div className="dlg-row"><button className="btn btn-outline" onClick={mf.declineShared} data-autofocus>Close</button></div>
          </>}
        </Modal>
      )}
    </>
  );
});

function NameDialog({ dlg, names, acres, onSave, onClose }: { dlg: Extract<Dlg, { t: 'name' }>; names: string[]; acres: number | null; onSave: (name: string) => void; onClose: () => void }) {
  const [name, setName] = useState(() => (dlg.mode === 'rename' ? dlg.loc?.mine?.name ?? '' : nextName(names)));
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => { ref.current?.select(); }, []);
  const ok = name.trim().length > 0;
  return (
    <Modal title={dlg.mode === 'rename' ? 'Rename field' : 'Name your field'} onClose={onClose} testid="name-dialog">
      <form onSubmit={(e) => { e.preventDefault(); if (ok) onSave(name.trim()); }}>
        <label className="dlg-field"><span>Field name</span>
          <input ref={ref} value={name} onChange={(e) => setName(e.target.value)} maxLength={80} data-autofocus autoComplete="off" data-testid="name-input" /></label>
        {acres != null && <p className="dlg-text">About {fmtAc(acres)} acres</p>}
        <div className="dlg-row">
          <button type="button" className="btn btn-outline" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={!ok} data-testid="name-save">{dlg.mode === 'rename' ? 'Save name' : 'Save field'}</button>
        </div>
      </form>
    </Modal>
  );
}
