// The pieces of the field panel and the pick list that belong to a field the user drew:
// MineHead ("Your field" and the options menu), MineNotices (save error, simplified outline, what it spans),
// MineFacts (what grows inside it, from the USDA crop map and the state's field map) and MyFieldsGroup (the pick list's top group).
import { useEffect, useRef, useState } from 'react';
import './draw.css';
import Icon from '../Icons';
import { t, tx, locale } from '../../i18n';
import { acres, cropName, county, latestCrop } from '../ui/shared';
import { shareUrl } from '../../myFields';
import type { Location } from '../../types';

export type MineAction = 'rename' | 'redraw' | 'delete';
const list = (xs: string[]) => (xs.length < 2 ? xs.join('') : `${xs.slice(0, -1).join(', ')}${t('mf.and')}${xs[xs.length - 1]}`);

async function copyText(text: string) {
  try { await navigator.clipboard.writeText(text); return true; } catch { /* fall back to a hidden field */ }
  try {
    const t = document.createElement('textarea');
    t.value = text; t.style.position = 'fixed'; t.style.opacity = '0'; document.body.appendChild(t); t.select();
    const ok = document.execCommand('copy'); t.remove(); return ok;
  } catch { return false; }
}

export function MineHead({ loc, onAction }: { loc: Location; onAction: (a: MineAction) => void }) {
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState('');
  const wrap = useRef<HTMLDivElement>(null);
  const sp = loc.spot!, saved = !loc.mine?.draft || sp.state === 'ready';
  useEffect(() => {
    if (!open) return;
    const off = (e: Event) => { if (!wrap.current?.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') { setOpen(false); wrap.current?.querySelector<HTMLElement>('.mine-opt')?.focus(); } };
    document.addEventListener('mousedown', off); document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('mousedown', off); document.removeEventListener('keydown', esc); };
  }, [open]);
  useEffect(() => { setOpen(false); setNote(''); }, [loc.id]);
  const pick = (a: MineAction) => { setOpen(false); onAction(a); };
  const copy = async () => {
    setNote((await copyText(shareUrl(loc.id))) ? t('mf.copied') : t('mf.nocopy'));
    setTimeout(() => { setOpen(false); setNote(''); }, 1100);
  };
  return (
    <div className="mine-head" data-testid="mine-head">
      <p className="spot-label" data-testid="mine-label"><i className={`live-dot ${sp.state}`} />{t('mf.your')}</p>
      <div className="mine-menu" ref={wrap}>
        <button className="btn btn-outline btn-sm mine-opt" onClick={() => setOpen(!open)} aria-haspopup="menu" aria-expanded={open} disabled={!saved} data-testid="mine-menu-btn">{t('mf.options')}<Icon name="down" size={16} /></button>
        {open && (
          <div className="mine-pop" role="menu" data-testid="mine-menu">
            <button role="menuitem" onClick={() => pick('rename')} data-testid="mine-rename"><Icon name="draw" />{t('mf.rename')}</button>
            <button role="menuitem" onClick={() => pick('redraw')} data-testid="mine-redraw"><Icon name="shape" />{t('mf.redraw')}</button>
            <button role="menuitem" onClick={copy} data-testid="mine-share"><Icon name="copy" />{note || t('mf.share')}</button>
            <button role="menuitem" className="danger" onClick={() => pick('delete')} data-testid="mine-delete"><Icon name="trash" />{t('mf.delete')}</button>
          </div>
        )}
      </div>
    </div>
  );
}

/** Under the field name: a save that failed, a simplified outline, and what the outline spans. */
export function MineNotices({ loc, onRetry, onFix }: { loc: Location; onRetry?: () => void; onFix: () => void }) {
  const m = loc.mine!, sp = loc.spot!;
  const s = m.spans;
  // the API lists the county again among the districts, and writes subbasins in capitals
  const nice = (x: string) => (x === x.toUpperCase() ? x.toLowerCase().replace(/(^|[\s-])([a-z])/g, (_, a, c) => a + c.toUpperCase()) : x);
  const counties = (s?.counties ?? []).map((c) => t('mf.county', { c: c.replace(/ County$/i, '') }));
  const parts = s ? [...counties, ...(s.districts ?? []).filter((d) => !counties.some((c) => c.toLowerCase() === d.toLowerCase())), ...(s.gsas ?? []), ...(s.subbasins ?? []).map((b) => { const n = nice(b); return /basin|cuenca/i.test(n) ? n : t('mf.basin', { n }); })] : [];
  return (
    <>
      {sp.state === 'error' && (
        <div className="notice spot-notice" role="alert" data-testid="mine-error">
          <span>{sp.error}</span>
          {m.errorKind === 'invalid' ? <button className="btn btn-outline btn-sm" onClick={onFix} data-testid="mine-fix">{t('mf.fix')}</button>
            : onRetry && <button className="btn btn-outline btn-sm" onClick={onRetry} data-testid="mine-retry">{t('mf.retry')}</button>}
        </div>
      )}
      {sp.state === 'ready' && m.simplified?.reason && <p className="mine-note" data-testid="mine-simplified">{m.simplified.reason}</p>}
      {sp.state === 'ready' && parts.length > 0 && <p className="mine-spans" data-testid="mine-spans">{t('mf.spans', { list: list(parts) })}</p>}
    </>
  );
}

// Land IQ / DWR crop classes, first letter of the code (state field map)
const DWR_CLASS: Record<string, string> = { C: tx('Citrus and subtropical'), D: tx('Deciduous fruits and nuts'), F: tx('Field crops'), G: tx('Grain and hay'), I: tx('Idle'), P: tx('Pasture'), R: tx('Rice'), T: tx('Truck, nursery and berry crops'), V: tx('Vineyard'), Y: tx('Young orchard or vineyard'), U: tx('Urban'), S: tx('Semi-agricultural'), X: tx('Unclassified') };
const dwrCrop = (code: string) => { const c = (code ?? '').trim(); return c ? `${DWR_CLASS[c[0].toUpperCase()] ?? t('mf.crop')} (${c})` : t('mf.cropNone'); };

/** What grows inside the outline: the crop map's mix for the latest year, and the state's mapped fields it overlaps. */
export function MineFacts({ loc }: { loc: Location }) {
  const m = loc.mine!;
  if (loc.spot?.state !== 'ready') return null;
  const years = Object.keys(m.crop_mix ?? {}).map(Number).sort((a, b) => b - a);
  const mixText = (y: number) => (m.crop_mix![y] ?? []).map((c) => `${cropName(c.crop)} ${Math.round(c.share * 100)}%`).join(', ');
  const dwr = m.dwr_fields ?? [], dwrAc = dwr.reduce((a, f) => a + (f.acres ?? 0), 0);
  const parts = m.parts?.items ?? [];
  const showParts = parts.length > 1 || parts.some((x) => x.holes > 0);
  if (!years.length && !dwr.length && !showParts) return null;
  return (
    <dl className="answers mine-facts" data-testid="mine-facts">
      {showParts && (
        <div className="ans" data-testid="mine-parts">
          <dt>{t('mf.parts')}</dt>
          <dd>{parts.map((x) => <span key={x.part}><b className="mine-yr">{t('mf.part', { n: x.part })}</b> {t(x.holes ? (x.holes === 1 ? 'mf.partHole' : 'mf.partHoles') : 'mf.partAc', { a: x.acres >= 10 ? Math.round(x.acres) : x.acres.toFixed(1), h: x.holes })}</span>)}</dd>
        </div>
      )}
      {years.length > 0 && (
        <div className="ans" data-testid="mine-mix">
          <dt>{t('mf.mixQ')}</dt>
          <dd><b>{years[0]}</b><span>{mixText(years[0])}.</span><cite>{t('mf.cdl')}</cite></dd>
        </div>
      )}
      {years.length > 1 && (
        <div className="ans d-only">
          <dt>{t('mf.earlier')}</dt>
          <dd>{years.slice(1, 5).map((y) => <span key={y}><b className="mine-yr">{y}</b> {mixText(y)}</span>)}</dd>
        </div>
      )}
      {dwr.length > 0 && (
        <div className="ans d-only" data-testid="mine-dwr">
          <dt>{t('mf.dwrT')}</dt>
          <dd>
            <span>{t(dwr.length === 1 ? 'mf.dwr1' : 'mf.dwrn', { n: dwr.length, a: Math.round(dwrAc).toLocaleString(locale) })}</span>
            {dwr.slice(0, 8).map((f) => <span key={f.id} className="mine-dwr-row">{t('mf.dwrRow', { crop: dwrCrop(f.crop), a: Math.round(f.acres) })} <small>{t('mf.dwrNo', { id: f.id })}</small></span>)}
            {dwr.length > 8 && <span className="muted">{t('mf.more', { n: dwr.length - 8 })}</span>}
            <cite>{t('mf.dwrSrc')}</cite>
          </dd>
        </div>
      )}
    </dl>
  );
}

/** A small outline of the field (no satellite picture exists for a field the user drew). */
function Outline({ loc }: { loc: Location }) {
  const g = loc.mine?.geometry ?? loc.geometry;
  const polys = g.type === 'Polygon' ? [g.coordinates] : g.coordinates;
  const k = Math.cos((loc.centroid.lat * Math.PI) / 180);
  const all = polys.flatMap((p) => p[0]);
  const xs = all.map((p) => p[0] * k), ys = all.map((p) => -p[1]);
  const x0 = Math.min(...xs), y0 = Math.min(...ys), w = Math.max(...xs) - x0 || 1e-6, h = Math.max(...ys) - y0 || 1e-6, s = 40 / Math.max(w, h);
  const ox = (48 - w * s) / 2, oy = (48 - h * s) / 2;
  const d = polys.map((rings) => rings.map((r) => 'M' + r.map((p) => `${((p[0] * k - x0) * s + ox).toFixed(1)},${((-p[1] - y0) * s + oy).toFixed(1)}`).join('L') + 'Z').join('')).join('');
  return <svg viewBox="0 0 48 48" aria-hidden="true"><path d={d} fillRule="evenodd" /></svg>;
}

/** "My fields" at the top of the pick list: one row per drawn field (name, acres, last crop) and the way to draw another. */
export function MyFieldsGroup({ locs, selectedId, onSelect, onDraw }: { locs: Location[]; selectedId: string | null; onSelect: (id: string) => void; onDraw: () => void }) {
  return (
    <section className="mine-group" aria-label={t('mf.mine')} data-testid="my-fields">
      <div className="mine-group-head">
        <h2 className="pk-group-h">{t('mf.mine')}</h2>
        <button className="btn btn-secondary btn-sm" onClick={onDraw} data-testid="draw-from-list"><Icon name="draw" size={16} />{t('mf.drawBtn')}</button>
      </div>
      {locs.length === 0 && <p className="mine-empty">{t('mf.empty')}</p>}
      {locs.length > 0 && (
        <ul className="pk-list mine-list">
          {locs.filter((l) => l.id !== 'my_draft').map((l, i) => {
            const last = Object.keys(l.crop_history).length ? latestCrop(l).crop : l.mine?.lastCrop ? cropName(l.mine.lastCrop) : null;
            return (
              <li key={l.id} style={{ '--i': Math.min(i, 8) } as React.CSSProperties}>
                <button className={`pk-row mine-row ${selectedId === l.id ? 'on' : ''}`} aria-current={selectedId === l.id ? 'true' : undefined} onClick={() => onSelect(l.id)} data-testid={`mine-row-${i}`}>
                  <span className="mine-thumb"><Outline loc={l} /></span>
                  <span className="pk-body">
                    <b>{l.mine?.name ?? l.farmer_name}</b>
                    <span className="pk-facts">{last ? t('mf.acLast', { a: acres(l), last: last.toLowerCase() }) : t('mf.partAc', { a: acres(l) })}</span>
                    <span className="pk-note">{l.county_name ? t('mf.county', { c: county(l) }) : t('mf.yourOutline')}</span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
