// "List" view of the map: every field, catalog farm and (when a BC field has them in view) reserve as a keyboard list, plus
// "Find a field by address or coordinates" ("lat, lon", or a place name through the free Nominatim geocoder).
import { useEffect, useMemo, useRef, useState } from 'react';
import type { Location } from '../../types';
import type { CatalogItem } from '../week/catalog';
import { acres, fieldName, latestCrop, place } from '../ui/shared';
import { isBC } from '../../api';
import Icon from '../Icons';

export interface ReserveRow { name: string; lat: number; lon: number; km?: number }
interface Row { key: string; kind: 'Field' | 'Farm' | 'Reserve'; name: string; crop: string; acres: string; region: string; go: () => void }

/** "37.3, -120.5" or "37.3 -120.5" to [lat, lon]; null when it is not a coordinate pair. */
export function parseCoords(s: string): [number, number] | null {
  const m = /^\s*(-?\d{1,3}(?:\.\d+)?)\s*[,;\s]\s*(-?\d{1,3}(?:\.\d+)?)\s*$/.exec(s);
  if (!m) return null;
  const a = +m[1], b = +m[2];
  if (Math.abs(a) <= 90 && Math.abs(b) <= 180) return [a, b];
  return null;
}

/** A place name to the first match (OpenStreetMap Nominatim; light use, one request per search, nothing personal sent). */
async function geocode(q: string): Promise<{ lat: number; lon: number; label: string } | null> {
  const r = await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&accept-language=en&q=${encodeURIComponent(q)}`, { headers: { Accept: 'application/json' } });
  if (!r.ok) throw new Error(String(r.status));
  const j = (await r.json()) as { lat: string; lon: string; display_name: string }[];
  return j[0] ? { lat: +j[0].lat, lon: +j[0].lon, label: j[0].display_name } : null;
}

export function MapList(p: { locations: Location[]; catalog: CatalogItem[]; reserves: ReserveRow[]; onField: (id: string) => void; onFarm: (it: CatalogItem) => void; onReserve: (r: ReserveRow) => void; onFind: (lat: number, lon: number) => void; onClose: () => void }) {
  const [q, setQ] = useState('');
  const [find, setFind] = useState('');
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const box = useRef<HTMLElement>(null);
  const rows = useMemo<Row[]>(() => [
    ...p.locations.filter((l) => !l.id.startsWith('pt_')).map((l): Row => { const c = latestCrop(l); return { key: l.id, kind: 'Field', name: fieldName(l), crop: `${c.crop}${c.year ? ` (${c.year})` : ''}`, acres: `${acres(l)} acres`, region: place(l), go: () => p.onField(l.id) }; }),
    ...p.catalog.map((it): Row => ({ key: it.id, kind: 'Farm', name: it.name, crop: it.crop_group_label, acres: it.acres ? `${Math.round(it.acres)} acres` : 'acres not listed', region: it.area, go: () => p.onFarm(it) })),
    ...p.reserves.map((r): Row => ({ key: `res-${r.name}`, kind: 'Reserve', name: r.name, crop: 'Reserve land (context)', acres: 'acres not listed', region: r.km != null ? `${r.km.toFixed(0)} km from the field` : 'British Columbia', go: () => p.onReserve(r) })),
  ], [p.locations, p.catalog, p.reserves]); // eslint-disable-line react-hooks/exhaustive-deps
  const words = q.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const shown = rows.filter((r) => words.every((w) => `${r.name} ${r.crop} ${r.region} ${r.kind}`.toLowerCase().includes(w)));
  useEffect(() => { box.current?.querySelector<HTMLElement>('[data-autofocus]')?.focus(); }, []);
  const arrow = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') { e.stopPropagation(); p.onClose(); return; }
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
    const items = [...(box.current?.querySelectorAll<HTMLElement>('.ml-row') ?? [])];
    const i = items.indexOf(document.activeElement as HTMLElement);
    if (i < 0 && e.key === 'ArrowDown') { e.preventDefault(); items[0]?.focus(); return; }
    if (i < 0) return;
    e.preventDefault(); items[Math.max(0, Math.min(items.length - 1, i + (e.key === 'ArrowDown' ? 1 : -1)))]?.focus();
  };
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const s = find.trim(); if (!s) return;
    const c = parseCoords(s);
    if (c) { setMsg(`Opening ${c[0].toFixed(4)}, ${c[1].toFixed(4)}.`); p.onFind(c[0], c[1]); return; }
    setBusy(true); setMsg('Searching…');
    try {
      const g = await geocode(s);
      if (!g) setMsg('No place found. Try a town and state, or coordinates like 39.2, -122.0.');
      else { setMsg(`Opening ${g.label.split(',').slice(0, 2).join(',')}.`); p.onFind(g.lat, g.lon); }
    } catch { setMsg('The place search did not answer. Try coordinates like 39.2, -122.0.'); }
    setBusy(false);
  };
  return (
    <section className="map-list" ref={box} aria-label="List of fields" data-testid="map-list" onKeyDown={arrow}>
      <header><h2>Fields, farms and reserves</h2><button className="icon-btn" onClick={p.onClose} aria-label="Close the list" data-testid="list-close"><Icon name="close" size={20} /></button></header>
      <form className="ml-find" onSubmit={submit} role="search">
        <label htmlFor="ml-find">Find a field by address or coordinates</label>
        <div><input id="ml-find" type="search" value={find} onChange={(e) => setFind(e.target.value)} placeholder="Town, address, or 39.2, -122.0" autoComplete="off" data-testid="find-input" data-autofocus /><button className="btn btn-primary" type="submit" disabled={busy}>Find</button></div>
        <p className="muted" role="status" aria-live="polite">{msg}</p>
      </form>
      <label className="ml-filter">Filter the list<input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Name, crop, county" data-testid="list-filter" /></label>
      <p className="muted" role="status" aria-live="polite">{shown.length} of {rows.length} places</p>
      <ul className="ml-list">
        {shown.map((r) => (
          <li key={r.key}><button className="ml-row" onClick={r.go} data-testid={`list-${r.key}`}>
            <b>{r.name}</b><span><i className={`ml-kind k-${r.kind}`}>{r.kind}</i>{r.crop} · {r.acres} · {r.region}</span>
          </button></li>
        ))}
      </ul>
    </section>
  );
}
