// "My fields": fields the user drew. The id (`my_...`) is the field: it carries the name and the outline, so any server can
// rebuild it. This file holds the client side: the saved list (localStorage["myFields"] = [{id, name}]), the calls to
// /api/my-fields, and a hook that gives App the drawn fields as ordinary `Location`s (with `spot` and `mine` set, so the
// panel reuses the tapped-spot sections: only `ready` parts show data, `unavailable` ones get one quiet line).
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { API_BASE, P, baseFor, isMine, realLocation, type ProvMap } from './api';
import { haToAc } from './lib';
import type { Location, MineInfo } from './types';

export const DRAFT_ID = 'my_draft';
export interface MyRef { id: string; name: string }
export type Polygon = { type: 'Polygon'; coordinates: number[][][] };
export type MultiPolygon = { type: 'MultiPolygon'; coordinates: number[][][][] };
/** What the API takes and returns: one outline (holes allowed) or several parts. */
export type Geom = Polygon | MultiPolygon;
/** Every part as its rings (shell first, then holes). */
export const partsOf = (g: Geom): number[][][][] => (g.type === 'Polygon' ? [g.coordinates] : g.coordinates);
/** Area in hectares: parts minus holes. */
export const geomAreaHa = (g: Geom) => partsOf(g).reduce((a, rings) => a + rings.reduce((b, r, i) => b + (i === 0 ? 1 : -1) * ringAreaM2(openRing(r)), 0), 0) / 1e4;
/** Why a call failed: `invalid` is a 422 whose `message` is the API's farmer-readable detail, shown as written. */
export interface Failure { kind: 'invalid' | 'busy' | 'timeout' | 'network' | 'failed'; message: string; retryAfter?: number }
export interface Submit { name: string; geometry: Geom; /** a rename or redraw: this id is forgotten once the new one is saved */ replaceId?: string }
interface ListItem { id: string; name: string; acres: number; area_ha: number; centroid: { lon: number; lat: number }; bbox: number[]; geometry: Geom; computed?: boolean; family?: string; county_name?: string | null; last_crop?: string | null }

// ---------- the saved list (every read and write guarded: storage can be blocked or full) ----------
const KEY = 'myFields';
export function loadRefs(): MyRef[] {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) ?? '[]');
    return Array.isArray(v) ? v.filter((x) => x && typeof x.id === 'string' && x.id.startsWith('my_') && x.id !== DRAFT_ID && typeof x.name === 'string') : [];
  } catch { return []; }
}
export function saveRefs(refs: MyRef[]) { try { localStorage.setItem(KEY, JSON.stringify(refs)); } catch { /* storage blocked or full: the list lives for this visit only */ } }

// ---------- share links: #field=my_... ----------
export const shareUrl = (id: string) => `${location.origin}${location.pathname}#field=${id}`;
export const parseFieldHash = () => /^#field=(my_[A-Za-z0-9_-]+)$/.exec(location.hash)?.[1] ?? null;

// ---------- geometry ----------
const R = 6371008.8;
/** Area of a lon/lat ring in square metres (equirectangular about its own latitude: within 0.1% at field size). */
export function ringAreaM2(ring: number[][]): number {
  if (ring.length < 3) return 0;
  const lat0 = (ring.reduce((a, p) => a + p[1], 0) / ring.length) * Math.PI / 180;
  let a = 0;
  for (let i = 0; i < ring.length; i++) {
    const [x1, y1] = ring[i], [x2, y2] = ring[(i + 1) % ring.length];
    a += (x1 * Math.PI / 180) * Math.cos(lat0) * R * (y2 * Math.PI / 180) * R - (x2 * Math.PI / 180) * Math.cos(lat0) * R * (y1 * Math.PI / 180) * R;
  }
  return Math.abs(a) / 2;
}
export const ringAcres = (ring: number[][]) => haToAc(ringAreaM2(ring) / 1e4);
/** The ring without its closing duplicate, and without repeated neighbours (an in-progress shape has the cursor in it). */
export function openRing(ring: number[][]): number[][] {
  const out = ring.filter((p, i) => i === 0 || p[0] !== ring[i - 1][0] || p[1] !== ring[i - 1][1]);
  if (out.length > 1 && out[0][0] === out[out.length - 1][0] && out[0][1] === out[out.length - 1][1]) out.pop();
  return out;
}
const centroidOf = (g: Geom) => { const r = partsOf(g).flatMap((p) => p[0]); const xs = r.map((p) => p[0]), ys = r.map((p) => p[1]); return { lon: (Math.min(...xs) + Math.max(...xs)) / 2, lat: (Math.min(...ys) + Math.max(...ys)) / 2 }; };

// ---------- calls ----------
type Ok<T> = { ok: true; body: T } | { ok: false; err: Failure };
async function call<T>(path: string, init: RequestInit | undefined, ms: number): Promise<Ok<T>> {
  const ctl = new AbortController();
  const h = setTimeout(() => ctl.abort(), ms);
  try {
    const r = await fetch(`${API_BASE}${path}`, { ...init, signal: ctl.signal });
    if (r.ok) return { ok: true, body: await r.json() };
    let detail = '';
    try {
      const j = await r.json();
      detail = typeof j?.detail === 'string' ? j.detail : Array.isArray(j?.detail) ? j.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join('; ') : '';
    } catch { /* no body */ }
    if (r.status === 422) return { ok: false, err: { kind: 'invalid', message: detail || 'That outline cannot be used. Redraw it and try again.' } };
    if (r.status === 429) { const s = +(r.headers.get('Retry-After') ?? '') || undefined; return { ok: false, err: { kind: 'busy', message: `Busy right now. Try again${s ? ` in about ${s} seconds` : ' in a moment'}.`, retryAfter: s } }; }
    if (r.status === 504) return { ok: false, err: { kind: 'timeout', message: 'No answer after 50 seconds. Try again.' } };
    return { ok: false, err: { kind: 'failed', message: r.status === 400 ? 'That field link is not valid.' : 'The analysis did not work this time. Try again.' } };
  } catch {
    return { ok: false, err: ctl.signal.aborted ? { kind: 'timeout', message: 'No answer after 50 seconds. Try again.' } : { kind: 'network', message: 'Could not reach the CropLytics server, or it is busy. Try again in a moment.' } };
  } finally { clearTimeout(h); }
}
export const createField = (name: string, geometry: Geom) => call<Record<string, any>>('/my-fields', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ name, geometry }) }, 55000); // eslint-disable-line @typescript-eslint/no-explicit-any
export const getField = (id: string) => call<Record<string, any>>(`/my-fields/${id}`, undefined, 55000); // eslint-disable-line @typescript-eslint/no-explicit-any
async function listFields(ids: string[]): Promise<{ items: ListItem[]; invalid: string[] }> {
  const items: ListItem[] = [], invalid: string[] = [];
  for (let i = 0; i < ids.length; i += 50) {
    const r = await call<{ items: ListItem[]; invalid?: { id: string }[] }>(`/my-fields?ids=${ids.slice(i, i + 50).join(',')}`, undefined, 20000);
    if (r.ok) { items.push(...r.body.items); invalid.push(...(r.body.invalid ?? []).map((x) => x.id)); }
  }
  return { items, invalid };
}

// ---------- API payloads as Locations ----------
const mineInfo = (name: string, b: Record<string, any> | null, extra?: Partial<MineInfo>): MineInfo => ({ // eslint-disable-line @typescript-eslint/no-explicit-any
  name, geometry: b?.geometry, parts: b?.user_field?.parts, spans: b?.user_field?.spans, dwr_fields: b?.user_field?.dwr_fields, crop_mix: b?.user_field?.crop_mix, simplified: b?.user_field?.simplified ?? null, idNote: b?.id_note ?? null, ...extra });
/** The full payload (POST or GET /api/my-fields/{id}) as a Location and its provenance. */
export function fromPayload(b: Record<string, any>): { loc: Location; prov: ProvMap } { // eslint-disable-line @typescript-eslint/no-explicit-any
  const { loc, prov } = realLocation(baseFor(b), b);
  const name: string = b.name ?? b.farmer_name ?? 'My field';
  const sec = (b.sections ?? {}) as Record<string, { cropland?: boolean }>;
  prov.outline = P('outline', 'Your outline', 'api', 'The outline you drew');
  const first = b.geometry?.type === 'MultiPolygon' ? { type: 'Polygon' as const, coordinates: b.geometry.coordinates[0] } : b.geometry;
  return { prov, loc: { ...loc, geometry: first ?? loc.geometry, events: [], farmer_name: name, name, short_name: name, county_name: b.county_name ?? null, county: b.county_name ?? undefined,
    spot: { state: 'ready', lat: b.centroid.lat, lon: b.centroid.lon, sections: b.sections, fallbackSquare: false, cropland: sec.family?.cropland !== false }, mine: mineInfo(name, b) } };
}
/** A drawn field before its analysis is in: its outline and name, the panel in its skeleton state. */
function stub(id: string, name: string, g: Geom, extra: { areaHa?: number; family?: string; county?: string | null; lastCrop?: string | null; error?: Failure | null }): Location {
  const base = baseFor({ id, farmer_name: name, family: extra.family ?? 'forage', county_name: extra.county ?? undefined });
  const c = centroidOf(g), ha = extra.areaHa ?? geomAreaHa(g);
  return { ...base, id, name, short_name: name, farmer_name: name, headline: '', events: [], county: extra.county ?? undefined, county_name: extra.county ?? null, family: extra.family ?? 'other', region: 'ca', dwr_id: undefined,
    geometry: { type: 'Polygon', coordinates: partsOf(g)[0] }, centroid: c, area_ha: { value: ha, low: null, high: null, unit: 'ha', method: 'computed' }, crop_history: {},
    water: { ...base.water, allocation_input: { unit: 'acre-ft/acre', value: extra.family === 'rice' ? 5.0 : 3.0 } },
    spot: extra.error ? { state: 'error', lat: c.lat, lon: c.lon, error: extra.error.message } : { state: 'loading', lat: c.lat, lon: c.lon },
    mine: { name, draft: true, geometry: g, lastCrop: extra.lastCrop ?? null, errorKind: extra.error?.kind } };
}

// ---------- the hook ----------
interface Draft { args: Submit; error: Failure | null }
export interface SharedField { id: string; loc: Location | null; prov: ProvMap; known: boolean; error?: Failure }
export function useMyFields(selectedId: string | null) {
  const [refs, setRefs] = useState<MyRef[]>(loadRefs);
  const [items, setItems] = useState<Record<string, ListItem>>({});
  const [full, setFull] = useState<Record<string, { loc: Location; prov: ProvMap }>>({});
  const [fails, setFails] = useState<Record<string, Failure>>({});
  const [draft, setDraft] = useState<Draft | null>(null);
  const [shared, setShared] = useState<SharedField | null>(null);
  const [listed, setListed] = useState(false);
  const inflight = useRef(new Set<string>());
  const seq = useRef(0);
  const refsRef = useRef(refs);
  refsRef.current = refs;

  useEffect(() => { saveRefs(refs); }, [refs]);

  // the list: one cheap call (no upstream lookups) gives every row and outline
  useEffect(() => {
    const ids = loadRefs().map((r) => r.id);
    if (!ids.length) { setListed(true); return; }
    let ok = true;
    listFields(ids).then(({ items: its, invalid }) => {
      if (!ok) return;
      setItems(Object.fromEntries(its.map((i) => [i.id, i])));
      if (invalid.length) setRefs((rs) => rs.filter((r) => !invalid.includes(r.id)));
      setListed(true);
    });
    return () => { ok = false; };
  }, []);

  /** the full analysis of one listed field (when it is picked) */
  const load = useCallback(async (id: string, refresh = false) => {
    if (inflight.current.has(id)) return;
    inflight.current.add(id);
    setFails((f) => { const { [id]: _, ...rest } = f; return rest; });
    const r = await getField(refresh ? `${id}?refresh=1` : id);
    inflight.current.delete(id);
    if (r.ok) { const x = fromPayload(r.body); setFull((f) => ({ ...f, [id]: x })); }
    else setFails((f) => ({ ...f, [id]: r.err }));
  }, []);
  useEffect(() => {
    if (!selectedId || !isMine(selectedId) || selectedId === DRAFT_ID) return;
    if (!full[selectedId] && !fails[selectedId] && refs.some((r) => r.id === selectedId)) load(selectedId);
  }, [selectedId, full, fails, refs, load]);

  /** save a new field, a rename or a redraw: the panel shows at once in its skeleton state; resolves to the new id */
  const submit = useCallback(async (args: Submit): Promise<string | null> => {
    const my = ++seq.current;
    setDraft({ args, error: null });
    const r = await createField(args.name, args.geometry);
    if (my !== seq.current) return null;
    if (!r.ok) { setDraft({ args, error: r.err }); return null; }
    const x = fromPayload(r.body);
    setFull((f) => ({ ...f, [x.loc.id]: x }));
    setRefs((rs) => [{ id: x.loc.id, name: args.name }, ...rs.filter((q) => q.id !== x.loc.id && q.id !== args.replaceId)]);
    setDraft(null);
    return x.loc.id;
  }, []);
  const retryDraft = useCallback(() => draft ? submit(draft.args) : Promise.resolve(null), [draft, submit]);
  const dropDraft = useCallback(() => { seq.current++; setDraft(null); }, []);
  const remove = useCallback((id: string) => { setRefs((rs) => rs.filter((r) => r.id !== id)); setFull((f) => { const { [id]: _, ...rest } = f; return rest; }); }, []);
  const retry = useCallback((id: string) => { if (id === DRAFT_ID) return retryDraft(); setFails((f) => { const { [id]: _, ...rest } = f; return rest; }); return load(id); }, [load, retryDraft]);

  // a shared link (#field=my_...): fetch it, then ask before adding it to this person's list
  const openShared = useCallback((id: string) => {
    getField(id).then((r) => {
      if (r.ok) { const x = fromPayload(r.body); setShared({ id, ...x, known: refsRef.current.some((q) => q.id === id) }); }
      else setShared({ id, loc: null, prov: {}, known: false, error: r.err });
    });
  }, []);
  useEffect(() => {
    const id = parseFieldHash();
    if (id) openShared(id);
  }, [openShared]);
  const acceptShared = useCallback(() => {
    if (!shared?.loc) { setShared(null); return null; }
    const { id, loc, prov } = shared;
    setFull((f) => ({ ...f, [id]: { loc, prov } }));
    setRefs((rs) => (rs.some((r) => r.id === id) ? rs : [{ id, name: loc.mine?.name ?? 'Shared field' }, ...rs]));
    setShared(null);
    return id;
  }, [shared]);

  const locs = useMemo(() => {
    const out: Location[] = [];
    if (draft) out.push(stub(DRAFT_ID, draft.args.name, draft.args.geometry, { error: draft.error }));
    for (const r of refs) {
      const f = full[r.id];
      if (f) { out.push(f.loc); continue; }
      const it = items[r.id];
      if (it) out.push(stub(r.id, it.name ?? r.name, it.geometry, { areaHa: it.area_ha, family: it.family, county: it.county_name, lastCrop: it.last_crop, error: fails[r.id] }));
    }
    return out;
  }, [draft, refs, full, items, fails]);
  const prov = useMemo(() => Object.fromEntries(Object.entries(full).map(([id, x]) => [id, x.prov])), [full]);
  return { locs, prov, refs, listed, draft, shared, submit, retry, dropDraft, remove, acceptShared, openShared, declineShared: () => setShared(null), refresh: (id: string) => load(id, true) };
}
export type MyFields = ReturnType<typeof useMyFields>;

/** "My field 3": the first number not already used. */
export function nextName(existing: string[]): string {
  const used = new Set(existing.map((n) => n.trim().toLowerCase()));
  for (let i = 1; i < 500; i++) if (!used.has(`my field ${i}`)) return `My field ${i}`;
  return 'My field';
}
