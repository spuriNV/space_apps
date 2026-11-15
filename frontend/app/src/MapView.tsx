import { addCatalogLayers, setCatalogData, type CatalogItem } from './components/week/catalog';
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';
import maplibregl, { type GeoJSONSource, type StyleSpecification } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { acres, fieldName, latestCrop } from './components/ui/shared';
import type { BCInfo, Calendar, CellGrid, Dataset, Location, Regional } from './types';
import type { RegionalLive } from './api';
import { reserveName } from './components/ui/FirstNations';
import { atT, latestAt, dataT, tOf, TODAY_T, CLASS_LABEL, GRACE_RAMP, SMAP_RAMP, cellColor, cellHeight, cellState, clamp, fieldState, gridLayerFor, gridLayerLabel, ordinal, ramp, realCellState } from './lib';

// Tile sources fixed by CONTRACT.md (no API keys).
const ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
const STYLE: StyleSpecification = {
  version: 8,
  glyphs: 'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf',
  sources: {
    sat: { type: 'raster', tiles: [ESRI], tileSize: 256, maxzoom: 18, attribution: 'Imagery © Esri, Maxar, Earthstar Geographics' },
    omt: { type: 'vector', url: 'https://tiles.openfreemap.org/planet', attribution: '© OpenMapTiles © OpenStreetMap' },
  },
  layers: [
    { id: 'bg', type: 'background', paint: { 'background-color': '#0a0f15' } },
    { id: 'sat', type: 'raster', source: 'sat', paint: { 'raster-saturation': -0.08, 'raster-brightness-max': 0.92 } },
    { id: 'roads', type: 'line', source: 'omt', 'source-layer': 'transportation', minzoom: 8, filter: ['in', ['get', 'class'], ['literal', ['motorway', 'trunk', 'primary']]], paint: { 'line-color': 'rgba(255,236,170,0.5)', 'line-width': ['interpolate', ['linear'], ['zoom'], 8, 0.6, 14, 2.2] } },
    { id: 'admin', type: 'line', source: 'omt', 'source-layer': 'boundary', filter: ['all', ['<=', ['get', 'admin_level'], 4], ['!=', ['get', 'maritime'], 1]], paint: { 'line-color': 'rgba(255,255,255,0.6)', 'line-width': 1.1, 'line-dasharray': [3, 2] } },
    { id: 'place', type: 'symbol', source: 'omt', 'source-layer': 'place', filter: ['in', ['get', 'class'], ['literal', ['city', 'town', 'state']]],
      layout: { 'text-field': ['coalesce', ['get', 'name:en'], ['get', 'name']], 'text-font': ['Noto Sans Bold'], 'text-size': ['interpolate', ['linear'], ['zoom'], 4, ['match', ['get', 'class'], 'state', 14, 13], 12, 16], 'text-letter-spacing': ['match', ['get', 'class'], 'state', 0.18, 0.02], 'text-transform': ['match', ['get', 'class'], 'state', 'uppercase', 'none'], 'symbol-sort-key': ['get', 'rank'], 'text-padding': 6 },
      paint: { 'text-color': ['match', ['get', 'class'], 'state', 'rgba(255,255,255,0.75)', '#ffffff'], 'text-halo-color': 'rgba(5,10,16,0.85)', 'text-halo-width': 1.5 } },
  ],
};

/** Field marker: a paper-white map pin with a dark green edge and a crop-rows glyph (inline SVG). */
const PIN_SVG = `<svg class="pin-svg" width="28" height="36" viewBox="0 0 28 36" aria-hidden="true"><path class="pin-body" d="M14 1.2C7.2 1.2 2 6.3 2 12.9c0 8.4 10.2 20 11.1 21a1.2 1.2 0 0 0 1.8 0C15.8 32.9 26 21.3 26 12.9 26 6.3 20.8 1.2 14 1.2z"/><rect class="pin-field" x="8.5" y="7.5" width="11" height="11" rx="1.5"/><path class="pin-rows" d="M11 9.5v7M14 9.5v7M17 9.5v7"/></svg>`;

export const HOME = { center: [-119.9, 37.35] as [number, number], zoom: 5.75, pitch: 0, bearing: 0 };
const EXPLODE_Z0 = 12.5, EXPLODE_Z1 = 14.2;
const explodeExpr = (key: string) => ['interpolate', ['linear'], ['zoom'], EXPLODE_Z0, 0, EXPLODE_Z1, ['get', key]] as unknown as number;

export interface MapHandle {
  flyToField: (loc: Location, mode: 'card' | 'drill' | 'story' | 'year') => void;
  flyHome: () => void;
  flyTo: (lat: number, lon: number, zoom: number) => void;
  zoomBy: (d: number) => void;
  resetNorth: () => void;
  toggle3D: () => void;
  /** a tapped spot: centre it beside the panel, zooming in only if the map is far out */
  focusSpot: (lat: number, lon: number) => void;
  /** a field the user drew: fit its outline beside the panel (no zoom-out to the state view) */
  fitField: (loc: Location) => void;
  getMap: () => maplibregl.Map | null;
  /** fly in from the California view, draw the outline, raise the squares and replay every quarter 2016-2026; false when the field has no grid */
  replay: (loc: Location) => boolean;
  cancelReplay: () => void;
}
interface Props {
  locations: Location[]; bc: BCInfo | null; datasets: Dataset[];
  /** BC: reserve outlines near the selected field, drawn muted for context only (not part of the analysis) */
  reserves?: GeoJSON.FeatureCollection | null;
  selected: Location | null; cells: CellGrid | null; cal: Calendar | null; regional: Regional | null;
  t: number; detector: 'rule' | 'ml'; metric: 'cover' | 'et'; layersOn: Record<string, boolean>; regionalLive: RegionalLive;
  leftInset: number; bottomInset: number; rightInset: number;
  onSelect: (id: string) => void; onBC: () => void;
  /** farm catalog pins (clustered, light) and the crop group they are filtered to */
  catalog?: CatalogItem[] | null; catGroup?: string | null; onCatalogPick?: (it: { id: string; lat: number; lon: number }) => void;
  /** a tap, click or long-press on open map (not on a field or a pin): analyse that spot */
  onTap?: (lat: number, lon: number) => void;
  /** the replay drives the app's time state (so the panel follows) and reports when it is running */
  onReplayT?: (t: number) => void; onReplayRunning?: (on: boolean) => void;
  onView: (v: { zoom: number; pitch: number; bearing: number; lat: number; lon: number }) => void;
}
interface StackLabel { key: string; ax: number; ay: number; color: string; tag: string; title: string; value: string; note: string }

const fc = (features: unknown[] = []) => ({ type: 'FeatureCollection', features }) as unknown as GeoJSON.FeatureCollection;
function bbox(loc: Location) {
  const r = loc.geometry.coordinates[0];
  const xs = r.map((p) => p[0]), ys = r.map((p) => p[1]);
  return { w: Math.min(...xs), e: Math.max(...xs), s: Math.min(...ys), n: Math.max(...ys) };
}
const mPerDeg = (lat: number) => ({ lat: 111320, lon: 111320 * Math.cos((lat * Math.PI) / 180) });
function rect(w: number, s: number, e: number, n: number, props: Record<string, unknown>) {
  return { type: 'Feature', properties: props, geometry: { type: 'Polygon', coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]] } };
}
function padded(loc: Location, padM: number, props: Record<string, unknown>) {
  const b = bbox(loc), m = mPerDeg(loc.centroid.lat);
  return rect(b.w - padM / m.lon, b.s - padM / m.lat, b.e + padM / m.lon, b.n + padM / m.lat, props);
}
const FP_OFFSET: Record<string, [number, number]> = { smap: [0.37, 0.6], imerg: [0.66, 0.3], grace: [0.44, 0.55] };

const MapView = forwardRef<MapHandle, Props>(function MapView(p, ref) {
  const el = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [ready, setReady] = useState(false);
  const [labels, setLabels] = useState<StackLabel[]>([]);
  const [zoomClass, setZoomClass] = useState('far');
  const live = useRef(p);
  live.current = p;
  const stackInfo = useRef<{ key: string; alt: number; color: string; tag: string; title: string; value: string; note: string; pad: number }[]>([]);
  const programmatic = useRef(false);
  const replaying = useRef(false);
  const replayStop = useRef<(() => void) | null>(null);
  const [replayTick, setReplayTick] = useState(0);
  const [replayOn, setReplayOn] = useState(false);
  const [caption, setCaption] = useState<{ head: string; sub: string } | null>(null);
  const reduceMotion = useRef(typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches);

  // ---------- create map ----------
  useEffect(() => {
    const map = new maplibregl.Map({ container: el.current!, style: STYLE, ...HOME, maxPitch: 70, attributionControl: false, fadeDuration: 0, preserveDrawingBuffer: true } as maplibregl.MapOptions);
    mapRef.current = map;
    (window as unknown as Record<string, unknown>).__map = map;
    map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');
    map.addControl(new maplibregl.ScaleControl({ maxWidth: 110, unit: 'metric' }), 'bottom-right');
    map.on('load', () => {
      el.current?.querySelector('.maplibregl-ctrl-attrib')?.classList.remove('maplibregl-compact-show');
      for (const id of ['fp', 'fpgrid', 'fplabel', 'field', 'shadow', 'posts', 'slab-grace', 'slab-smap', 'cells', 'reserves', 'outline-draw']) map.addSource(id, id === 'cells' ? { type: 'geojson', data: fc(), promoteId: 'id' } : { type: 'geojson', data: fc() });
      addCatalogLayers(map, (it) => live.current.onCatalogPick?.(it));
      // reserve outlines (BC, context only): muted, dotted, under the field outline; never filled
      map.addLayer({ id: 'res-casing', type: 'line', source: 'reserves', paint: { 'line-color': 'rgba(10,12,8,0.5)', 'line-width': 3.6 } });
      map.addLayer({ id: 'res-line', type: 'line', source: 'reserves', paint: { 'line-color': '#f1ecdd', 'line-opacity': 0.95, 'line-width': 2, 'line-dasharray': [3, 2] } });
      map.addLayer({ id: 'fp-fill', type: 'fill', source: 'fp', paint: { 'fill-color': ['get', 'color'], 'fill-opacity': ['interpolate', ['linear'], ['zoom'], 8, 0.1, 13, 0.03] } });
      map.addLayer({ id: 'fp-line', type: 'line', source: 'fp', paint: { 'line-color': ['get', 'color'], 'line-width': 2, 'line-dasharray': [2, 1.5] } });
      map.addLayer({ id: 'fpgrid-line', type: 'line', source: 'fpgrid', minzoom: 11.5, paint: { 'line-color': ['get', 'color'], 'line-width': 1, 'line-opacity': 0.75 } });
      map.addLayer({ id: 'shadow', type: 'fill', source: 'shadow', minzoom: EXPLODE_Z0, paint: { 'fill-color': '#000', 'fill-opacity': ['interpolate', ['linear'], ['zoom'], EXPLODE_Z0, 0, EXPLODE_Z1, 0.42] } });
      map.addLayer({ id: 'field-casing', type: 'line', source: 'field', paint: { 'line-color': 'rgba(0,0,0,0.65)', 'line-width': ['case', ['get', 'mine'], 6, 5] } });
      map.addLayer({ id: 'field-line', type: 'line', source: 'field', paint: { 'line-color': ['case', ['get', 'mine'], '#9be88a', ['get', 'selected'], '#ffffff', 'rgba(255,255,255,0.75)'], 'line-width': ['case', ['get', 'mine'], 3, 2] } }); // yours: a solid light-green line (presets are white)
      map.addLayer({ id: 'outline-draw-casing', type: 'line', source: 'outline-draw', layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: { 'line-color': 'rgba(0,0,0,0.6)', 'line-width': 7 } });
      map.addLayer({ id: 'outline-draw', type: 'line', source: 'outline-draw', layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: { 'line-color': '#ffd166', 'line-width': 3.5 } });
      map.addLayer({ id: 'field-hit', type: 'fill', source: 'field', paint: { 'fill-color': ['case', ['get', 'mine'], '#9be88a', '#fff'], 'fill-opacity': ['interpolate', ['linear'], ['zoom'], 9, ['case', ['get', 'mine'], 0.16, 0.25], 11.5, ['case', ['get', 'mine'], ['case', ['get', 'selected'], 0.2, 0.12], 0.02]] } });
      // the replay writes feature-state (col, hs = full height at stack zoom) on the cells; with none set, the paint falls back to the baked properties
      const ext = (id: string, opacity: number, minzoom: number) => map.addLayer({ id, type: 'fill-extrusion', source: id, minzoom, paint: { 'fill-extrusion-color': id === 'cells' ? ['to-color', ['coalesce', ['feature-state', 'col'], ['get', 'col']]] : ['get', 'col'], 'fill-extrusion-base': explodeExpr('b'), 'fill-extrusion-height': id === 'cells' ? ['interpolate', ['linear'], ['zoom'], EXPLODE_Z0, 0, EXPLODE_Z1, ['coalesce', ['feature-state', 'hs'], ['get', 'h']]] as unknown as number : explodeExpr('h'), 'fill-extrusion-opacity': opacity, 'fill-extrusion-vertical-gradient': true } });
      ext('posts', 0.55, EXPLODE_Z0 + 0.4);
      ext('slab-grace', 0.86, EXPLODE_Z0 + 0.1);
      ext('slab-smap', 0.84, EXPLODE_Z0 + 0.1);
      ext('cells', 0.97, 11.2);
      map.on('click', 'field-hit', (e) => { const id = e.features?.[0]?.properties?.id; if (id) live.current.onSelect(id); });
      // tap anywhere: a click or tap on open map, a right-click, or a long-press (touch) drops a pin and analyses the spot
      let lastTap = 0;
      const tap = (e: maplibregl.MapMouseEvent | maplibregl.MapTouchEvent) => {
        const tgt = (e.originalEvent?.target as Element | null);
        if (tgt?.closest?.('.maplibregl-marker, .maplibregl-ctrl')) return;
        if (map.queryRenderedFeatures(e.point, { layers: ['field-hit', 'cat-pt', 'cat-cluster'] }).length) return;
        if (Date.now() - lastTap < 700) return;
        lastTap = Date.now();
        live.current.onTap?.(e.lngLat.lat, e.lngLat.lng);
      };
      map.on('click', tap);
      map.on('contextmenu', (e) => { e.preventDefault(); tap(e); });
      let press: ReturnType<typeof setTimeout> | null = null;
      map.on('touchstart', (e) => { if (press) clearTimeout(press); press = e.originalEvent.touches.length === 1 ? setTimeout(() => tap(e), 550) : null; });
      for (const ev of ['touchend', 'touchmove', 'touchcancel', 'movestart'] as const) map.on(ev, () => { if (press) { clearTimeout(press); press = null; } });
      map.on('mouseenter', 'field-hit', () => (map.getCanvas().style.cursor = 'pointer'));
      map.on('mouseleave', 'field-hit', () => (map.getCanvas().style.cursor = ''));
      setReady(true);
    });

    // Scroll-driven drill-down. setPitch/setBearing call jumpTo → map.stop(), which resets
    // ScrollZoomHandler / touch zoom mid-gesture, so the wheel or pinch died before the stack opened.
    // Write the live transform instead (MapLibre 4.7 pitch setter updates matrices; it does not stop gestures).
    const tiltForZoom = (z: number) => {
      const f = clamp((z - (EXPLODE_Z0 - 0.3)) / (EXPLODE_Z1 - EXPLODE_Z0), 0, 1);
      return { pitch: f * 58, bearing: -22 * f };
    };
    const fieldInView = (sel: Location) => {
      const pt = map.project([sel.centroid.lon, sel.centroid.lat]);
      const w = map.getContainer().clientWidth, h = map.getContainer().clientHeight, m = 64;
      return pt.x >= -m && pt.y >= -m && pt.x <= w + m && pt.y <= h + m;
    };
    const applyExplodeTilt = () => {
      if (replaying.current) return;
      const sel = live.current.selected;
      if (!sel || !fieldInView(sel)) return;
      const target = tiltForZoom(map.getZoom());
      const tr = map.transform;
      if (Math.abs(tr.pitch - target.pitch) < 0.4 && Math.abs(tr.bearing - target.bearing) < 0.4) return;
      tr.pitch = target.pitch;
      tr.bearing = target.bearing;
      map.triggerRepaint();
      updateLabels();
    };
    map.on('zoom', () => {
      const gesturing = map.scrollZoom.isZooming() || map.touchZoomRotate.isActive();
      // A user pinch/wheel cancels an in-flight flyTo; don't let that flag keep the camera flat.
      if (gesturing) programmatic.current = false;
      if (!gesturing && (programmatic.current || map.isEasing())) return;
      applyExplodeTilt();
    });
    map.on('zoomend', () => { if (!map.isEasing()) applyExplodeTilt(); });
    const report = () => {
      const c = map.getCenter(), z = map.getZoom();
      live.current.onView({ zoom: z, pitch: map.getPitch(), bearing: map.getBearing(), lat: c.lat, lon: c.lng });
      setZoomClass(z < 8.2 ? 'far' : z < 12.4 ? 'mid' : 'near');
    };
    for (const ev of ['dragstart', 'rotatestart', 'pitchstart'] as const) map.on(ev, (e) => { if ((e as { originalEvent?: unknown }).originalEvent) replayStop.current?.(); }); // programmatic jumps carry no originalEvent
    map.on('moveend', () => { programmatic.current = false; report(); });
    map.on('move', () => { updateLabels(); });
    map.on('zoom', report);
    report();
    return () => { replayStop.current?.(); map.remove(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---------- markers ----------
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !p.locations.length) return;
    const ms: maplibregl.Marker[] = [];
    for (const loc of p.locations) {
      const d = document.createElement('button');
      d.className = loc.mine ? 'pin site mine-pin' : loc.spot ? 'pin site spot-pin' : 'pin site';
      d.dataset.id = loc.id;
      const lc = latestCrop(loc);
      d.innerHTML = `${PIN_SVG}<span class="pin-text"><b></b><i></i></span>`;
      d.querySelector('b')!.textContent = loc.spot && !loc.mine ? (loc.spot.state === 'ready' ? fieldName(loc) : 'Tapped spot') : fieldName(loc);
      d.querySelector('i')!.textContent = loc.mine ? `${acres(loc)} acres · yours` : loc.spot && loc.spot.state !== 'ready' ? 'Analysing this spot…' : `${acres(loc)} acres${Number.isFinite(lc.year) ? ` · ${lc.crop} in ${lc.year}` : ''}`;
      d.onclick = (ev) => { ev.stopPropagation(); live.current.onSelect(loc.id); };
      d.classList.toggle('on', live.current.selected?.id === loc.id);
      // the pin tip (14, 36 inside the 28 x 36 pin) sits on the field centroid; the label hangs to its right
      // a tapped spot's pin sits where the grower tapped, not on the outline's centre
      ms.push(new maplibregl.Marker({ element: d, anchor: 'bottom-left', offset: [-14, 0] }).setLngLat(loc.spot && !loc.mine ? [loc.spot.lon, loc.spot.lat] : [loc.centroid.lon, loc.centroid.lat]).addTo(map));
    }
    for (const pl of p.bc?.places ?? []) {
      const d = document.createElement('button');
      d.className = 'pin pin-bc';
      d.innerHTML = `<span class="pin-dot"></span><span class="pin-text"><b>${pl.name}</b><i>British Columbia · not set up yet</i></span>`;
      d.onclick = (ev) => { ev.stopPropagation(); live.current.onBC(); };
      ms.push(new maplibregl.Marker({ element: d, anchor: 'left', offset: [-9, 0] }).setLngLat([pl.lon, pl.lat]).addTo(map));
    }
    return () => ms.forEach((m) => m.remove());
  }, [p.locations, p.bc, ready]);

  useEffect(() => { document.querySelectorAll<HTMLElement>('.pin.site').forEach((el) => el.classList.toggle('on', el.dataset.id === p.selected?.id)); }, [p.selected, p.locations]);

  useEffect(() => { const map = mapRef.current; if (map && ready && p.catalog) setCatalogData(map, p.catalog, p.catGroup ?? null); }, [ready, p.catalog, p.catGroup]);

  // ---------- reserve outlines (BC, context only) with paper label boxes ----------
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const feats = p.reserves?.features ?? [];
    (map.getSource('reserves') as GeoJSONSource).setData(fc(feats));
    const mk = feats.map((f) => {
      const g = f.geometry as GeoJSON.Polygon | GeoJSON.MultiPolygon;
      const polys = g.type === 'Polygon' ? [g.coordinates] : g.coordinates;
      // label just east of the largest part, at its mid latitude, so the outline itself stays visible
      const ring = polys.map((pp) => pp[0]).sort((a, b) => b.length - a.length)[0] ?? [];
      const ys = ring.map((c) => c[1]), midY = (Math.min(...ys) + Math.max(...ys)) / 2;
      const at = [Math.max(...ring.map((c) => c[0])), midY];
      const pr = (f.properties ?? {}) as { name?: string; band?: string; nation?: string; distance_to_field_km?: number };
      const d = document.createElement('div');
      d.className = 'res-tag';
      d.innerHTML = `<b></b><i></i>`;
      d.querySelector('b')!.textContent = reserveName(pr.name ?? 'Reserve');
      d.querySelector('i')!.textContent = pr.nation ?? pr.band ?? '';
      return { km: pr.distance_to_field_km ?? 99, m: new maplibregl.Marker({ element: d, anchor: 'left', offset: [6, 0] }).setLngLat(at as [number, number]).addTo(map) };
    }).sort((a, b) => a.km - b.km);
    // neighbouring reserves: keep the nearer one's label when two boxes overlap
    const declutter = () => {
      const kept: DOMRect[] = [];
      for (const { m } of mk) {
        const el = m.getElement(); el.style.visibility = 'visible';
        const r = el.getBoundingClientRect();
        if (kept.some((k) => r.left < k.right + 4 && r.right > k.left - 4 && r.top < k.bottom + 2 && r.bottom > k.top - 2)) el.style.visibility = 'hidden'; else kept.push(r);
      }
    };
    map.on('move', declutter);
    const h = setTimeout(declutter, 0);
    return () => { clearTimeout(h); map.off('move', declutter); mk.forEach(({ m }) => m.remove()); };
  }, [ready, p.reserves]);

  // ---------- field outlines + footprints ----------
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    (map.getSource('field') as GeoJSONSource).setData(fc(p.locations.map((l) => ({ type: 'Feature', properties: { id: l.id, selected: l.id === p.selected?.id, mine: !!l.mine }, geometry: l.mine?.geometry ?? l.geometry }))));
    const fps: unknown[] = [], grids: unknown[] = [], lbls: unknown[] = [];
    if (p.selected?.spot?.fallbackSquare) {
      const b = bbox(p.selected);
      lbls.push({ type: 'Feature', properties: { color: '#ffd166', label: '200 m square around your tap, not a field outline' }, geometry: { type: 'Point', coordinates: [b.e, b.s] } });
    }
    if (p.selected) {
      const loc = p.selected, m = mPerDeg(loc.centroid.lat), b = bbox(loc);
      for (const ds of p.datasets) {
        if (!p.layersOn[ds.id]) continue;
        if (ds.group === 'regional') {
          const [ox, oy] = FP_OFFSET[ds.id] ?? [0.5, 0.5];
          const w = loc.centroid.lon - (ds.footprint_m * ox) / m.lon, s = loc.centroid.lat - (ds.footprint_m * oy) / m.lat;
          const e = w + ds.footprint_m / m.lon, n = s + ds.footprint_m / m.lat;
          fps.push(rect(w, s, e, n, { color: ds.color }));
          lbls.push({ type: 'Feature', properties: { color: ds.color, label: `${({ grace: 'Groundwater', smap: 'Soil moisture', imerg: 'Rainfall', modis: 'Greenness' } as Record<string, string>)[ds.id] ?? ds.name}: this ${(ds.footprint_m / 1609).toFixed(0)}-mile square${ds.id === 'smap' && !live.current.regionalLive.smap ? ' (still downloading)' : ''}` }, geometry: { type: 'Point', coordinates: [e, n] } });
        } else if (ds.id !== 'hls') {
          const pad = ds.footprint_m * 2, lines: number[][][] = [];
          const w = b.w - pad / m.lon, e = b.e + pad / m.lon, s = b.s - pad / m.lat, n = b.n + pad / m.lat;
          for (let x = w; x <= e + 1e-9; x += ds.footprint_m / m.lon) lines.push([[x, s], [x, n]]);
          for (let y = s; y <= n + 1e-9; y += ds.footprint_m / m.lat) lines.push([[w, y], [e, y]]);
          grids.push({ type: 'Feature', properties: { color: ds.color }, geometry: { type: 'MultiLineString', coordinates: lines } });
          lbls.push({ type: 'Feature', properties: { color: ds.color, label: `${ds.name} · ${ds.native_scale} grid` }, geometry: { type: 'Point', coordinates: [e, s] } });
        }
      }
    }
    (map.getSource('fp') as GeoJSONSource).setData(fc(fps));
    (map.getSource('fpgrid') as GeoJSONSource).setData(fc(grids));
    // footprint labels: solid label boxes with an ink border (HTML markers), never bare text over imagery
    const mk = (lbls as { properties: { color: string; label: string }; geometry: { coordinates: [number, number] } }[]).map((l) => {
      const d = document.createElement('div');
      d.className = 'fp-tag';
      d.style.borderLeftColor = l.properties.color;
      d.textContent = l.properties.label;
      return new maplibregl.Marker({ element: d, anchor: 'top-right', offset: [-6, 6] }).setLngLat(l.geometry.coordinates).addTo(map);
    });
    return () => mk.forEach((m) => m.remove());
  }, [ready, p.locations, p.selected, p.layersOn, p.datasets, p.regionalLive.smap]);

  // ---------- exploded layer stack for the scrubber date ----------
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const set = (id: string, feats: unknown[]) => (map.getSource(id) as GeoJSONSource).setData(fc(feats));
    const { selected: loc, cells, cal, regional } = p;
    if (!loc || !cells || !cal) {
      for (const id of ['cells', 'slab-smap', 'slab-grace', 'posts', 'shadow']) if (!(replaying.current && id === 'cells')) set(id, []);
      stackInfo.current = [];
      updateLabels();
      return;
    }
    const S = (cells.cols * cells.cell_m) / 990; // keep proportions across field sizes
    const tt = dataT(cal, p.t); // past the last processed image, show the latest clear view
    const fs = fieldState(cal, tt, p.detector);
    const smap = regional ? latestAt(regional.smap_rootzone_pct.values, p.t)?.v ?? null : null;
    const grace = regional ? latestAt(regional.grace_gw_pct.values, p.t)?.v ?? null : null;
    const info: typeof stackInfo.current = [];
    const cellBase = 430 * S;
    if (p.layersOn.hls) {
      let sum = 0, n = 0;
      const layer = gridLayerFor(cells, tt);
      if (!replaying.current) set('cells', cells.features.map((f) => {
        const st = cells.layers ? realCellState(f.properties, layer, fs) : cellState(loc, fs, f.properties);
        if (st.cls !== 'u') { sum += p.metric === 'et' ? st.et : st.ndvi; n++; }
        return { type: 'Feature', geometry: f.geometry, properties: { id: f.properties.id, b: cellBase, h: cellBase + (8 + cellHeight(st, p.metric) * 175) * S, col: cellColor(st, f.properties, p.metric) } };
      }));
      const mean = n ? sum / n : 0;
      const real = !!cells.layers;
      info.push({ key: 'hls', alt: cellBase + 60 * S, pad: 0, color: '#7ee081', tag: real ? `Sentinel-2 satellite, 100 ft squares${p.metric === 'et' ? ' · water use is example numbers' : ''}` : 'Landsat and Sentinel-2, 100 ft squares · example numbers', title: p.metric === 'et' ? 'The crop: water it is using' : `The crop: ${CLASS_LABEL[fs.cls].toLowerCase()}`,
        value: (real ? !n : fs.cls === 'u') ? 'No clear view (cloud)' : p.metric === 'et' ? `${mean.toFixed(1)} mm/day (${(mean / 25.4).toFixed(2)} in/day)` : `Greenness ${mean.toFixed(2)} on a 0 to 1 scale`,
        note: real ? `${cells.features.length} squares · ${gridLayerLabel(layer)}` : `${cells.features.length} cells inside your field · ${p.detector === 'rule' ? 'rule' : 'ML'} detector${fs.disagree ? ' · detectors disagree' : ''}` });
    } else if (!replaying.current) set('cells', []);
    if (p.layersOn.smap) {
      const b = 235 * S, col = smap == null ? '#737a86' : ramp(SMAP_RAMP, smap);
      set('slab-smap', [padded(loc, 110 * S, { b, h: b + (14 + (smap ?? 10) * 0.42) * S, col })]);
      info.push({ key: 'smap', alt: b + 20 * S, pad: 110 * S, color: '#5ab0ff', tag: p.regionalLive.soilSource === 'grace_da' ? 'NASA GRACE-FO with a land model, root zone' : `NASA SMAP satellite${p.regionalLive.smap ? '' : ' · example numbers'}`, title: 'Soil moisture in the root zone', value: smap == null ? 'No reading' : `${smap >= 67 ? 'Wetter than usual' : smap > 33 ? 'About normal' : 'Drier than usual'} (${ordinal(Math.round(smap))} percentile)`,
        note: fs.cls === 'w' ? 'Reading is unreliable over standing water' : `One reading covers about ${Math.round(81 / (loc.area_ha.value / 100))} fields this size` });
    } else set('slab-smap', []);
    if (p.layersOn.grace) {
      const b = 45 * S, col = grace == null ? '#5d636e' : ramp(GRACE_RAMP, grace);
      set('slab-grace', [padded(loc, 230 * S, { b, h: b + (14 + (grace ?? 4) * 0.42) * S, col })]);
      info.push({ key: 'grace', alt: b + 16 * S, pad: 230 * S, color: '#ff7eb6', tag: `NASA GRACE-FO satellites${p.regionalLive.grace ? '' : ' · example numbers'}`, title: 'Groundwater in the basin', value: grace == null ? 'No reading: gap between satellite missions' : `${grace >= 67 ? 'More than usual' : grace > 33 ? 'About normal' : 'Less than usual'} (${ordinal(Math.round(grace))} percentile)`,
        note: 'Basin-wide signal, not your own well' });
    } else set('slab-grace', []);
    // corner posts tie the slabs together
    const bb = bbox(loc), m = mPerDeg(loc.centroid.lat), w = 5 * S;
    set('posts', info.length > 1 ? [[bb.w, bb.s], [bb.e, bb.s], [bb.e, bb.n], [bb.w, bb.n]].map(([x, y]) => rect(x - w / m.lon, y - w / m.lat, x + w / m.lon, y + w / m.lat, { b: 0, h: cellBase, col: '#e8eef7' })) : []);
    set('shadow', [padded(loc, 230 * S, {})]);
    stackInfo.current = info;
    updateLabels();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, p.selected, p.cells, p.cal, p.regional, p.regionalLive, p.t, p.detector, p.metric, p.layersOn, replayTick]);

  // a different field ends the replay
  useEffect(() => { replayStop.current?.(); }, [p.selected?.id]);

  // ---------- labels pinned to each slab (projected with altitude) ----------
  function updateLabels() {
    const map = mapRef.current, loc = live.current.selected;
    if (!map || !loc || !stackInfo.current.length) { setLabels((l) => (l.length ? [] : l)); return; }
    const f = clamp((map.getZoom() - EXPLODE_Z0) / (EXPLODE_Z1 - EXPLODE_Z0), 0, 1);
    if (f < 0.35) { setLabels((l) => (l.length ? [] : l)); return; }
    const tr = map.transform as unknown as { worldSize: number; pixelMatrix: ArrayLike<number> };
    const mtx = tr.pixelMatrix;
    if (!mtx) return;
    const b = bbox(loc), m = mPerDeg(loc.centroid.lat);
    const proj = (lng: number, lat: number, alt: number) => {
      const mc = maplibregl.MercatorCoordinate.fromLngLat([lng, lat]);
      const x = mc.x * tr.worldSize, y = mc.y * tr.worldSize, z = alt * f;
      const w = mtx[3] * x + mtx[7] * y + mtx[11] * z + mtx[15];
      return [(mtx[0] * x + mtx[4] * y + mtx[8] * z + mtx[12]) / w, (mtx[1] * x + mtx[5] * y + mtx[9] * z + mtx[13]) / w];
    };
    setLabels(stackInfo.current.map((s) => {
      const px = s.pad / m.lon, py = s.pad / m.lat;
      const corners = [[b.e + px, b.s - py], [b.e + px, b.n + py], [b.w - px, b.n + py], [b.w - px, b.s - py]].map(([x, y]) => proj(x, y, s.alt));
      const right = corners.reduce((a, c) => (c[0] > a[0] ? c : a));
      return { key: s.key, ax: right[0], ay: right[1], color: s.color, tag: s.tag, title: s.title, value: s.value, note: s.note };
    }));
  }


  // ---------- "Ten years from orbit": camera flight, outline draw, rising squares, then every quarter 2016-2026 ----------
  function startReplay(loc: Location): boolean {
    const map = mapRef.current, { cells, cal } = live.current;
    if (!map || !cells?.layers || !cal) return false;
    const frames = cells.layers.filter((l) => l.kind === 'quarter_median' && l.year != null && l.quarter != null && l.year >= 2016)
      .sort((a, b) => a.year! * 4 + a.quarter! - b.year! * 4 - b.quarter!);
    if (frames.length < 2) return false;
    replayStop.current?.();
    const RM = reduceMotion.current, S = (cells.cols * cells.cell_m) / 990, base = 430 * S, N = frames.length;
    const c01 = (x: number) => clamp(x, 0, 1);
    const lerp = (a: number, b: number, k: number) => a + (b - a) * k;
    const ease = (k: number) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
    const c = loc.centroid, small = loc.area_ha.value < 45;
    const g = loc.geometry, ring = (g.type === 'Polygon' ? g.coordinates[0] : g.coordinates[0][0]) as number[][];
    const cosLat = Math.cos((c.lat * Math.PI) / 180);
    const len = [0]; for (let i = 1; i < ring.length; i++) len.push(len[i - 1] + Math.hypot((ring[i][0] - ring[i - 1][0]) * cosLat, ring[i][1] - ring[i - 1][1]));
    const total = len[len.length - 1] || 1;
    // per cell: id, distance from the middle (the wave of rising squares), and a gap-filled series
    const feats = cells.features.map((f) => {
      const r = f.geometry.coordinates[0];
      const cx = r.reduce((a, q) => a + q[0], 0) / r.length, cy = r.reduce((a, q) => a + q[1], 0) / r.length;
      let prev: number | null = null;
      const v = frames.map((fr) => { const x = f.properties.nd?.[fr.key]; if (x != null) prev = x; return x ?? prev; });
      const first = v.find((x) => x != null) ?? null;
      return { f, id: f.properties.id, d: Math.hypot((cx - c.lon) * cosLat, cy - c.lat), v: v.map((x) => x ?? first) };
    });
    const maxD = Math.max(...feats.map((x) => x.d)) || 1;
    feats.forEach((x) => (x.d /= maxD));
    // state per frame: colour and height from the same functions the scrubber uses
    const frameStates = frames.map((fr, i) => {
      const tq = tOf(fr.year!, (fr.quarter! - 1) * 9 + 4), fs = fieldState(cal, dataT(cal, tq), live.current.detector);
      return feats.map((x) => { const st = x.v[i] == null ? { cls: 'u' as const, ndvi: 0, et: 0 } : realCellState({ ...x.f.properties, nd: { [fr.key]: x.v[i] } }, fr, fs); return { col: cellColor(st, x.f.properties, 'cover'), h: base + (8 + cellHeight(st, 'cover') * 175) * S }; });
    });
    const meanOf = (i: number) => feats.reduce((a, x) => a + (x.v[i] ?? 0), 0) / feats.length;
    const dry2022 = frames.map((fr, i) => (fr.year === 2022 ? meanOf(i) : null)).filter((x): x is number => x != null);
    const dryYear = dry2022.length >= 3 && dry2022.every((x) => x < 0.2);
    const hist = (loc.crop_history ?? {}) as Record<string, string>;
    const QN = ['Jan to Mar', 'Apr to Jun', 'Jul to Sep', 'Oct to Dec'];
    const captionFor = (year: number) => {
      if (year === 2022 && dryYear) return { head: '2022: water ran short. The field stayed bare all year.', sub: 'No green-up in any quarter. Compare 2021 and 2023.' };
      const crop = hist[String(year)];
      return { head: crop ? `${year}: ${crop.replace('Fallow/Idle Cropland', 'fallow')}` : `${year}`, sub: crop ? 'USDA crop record, as the satellites saw it' : 'Satellite record only; USDA crop record not out yet' };
    };
    // timeline (s): fly, draw, rise, then the quarters; 2022 plays slowly where the data is dry
    const T = RM ? { fly: [0, 0], line: [0, 0], rise: [0, 0] } : { fly: [0, 5.2], line: [3.8, 5.8], rise: [5.4, 6.6] };
    const lapse = T.rise[1] + 1.0;
    const keys: number[] = [lapse];
    for (let i = 1; i < N; i++) keys.push(keys[i - 1] + (RM ? 0.9 : dryYear && (frames[i].year === 2022 || (frames[i].year === 2023 && frames[i].quarter === 1)) ? 0.8 : 0.28));
    const END = keys[N - 1] + (RM ? 0.9 : 2.2);
    const frameAtT = (t: number) => { let i = 0; while (i + 1 < N && keys[i + 1] <= t) i++; return i; };
    // cameras: from the California view to the same camera as flyToField(loc, 'year')
    const ex = live.current.rightInset + 330;
    const pd = { ...pad(), right: ex };
    const end = { center: [c.lon, c.lat - (small ? 0.0006 : 0.001)] as [number, number], zoom: (small ? 15.15 : 14.5) - 0.75, pitch: 52, bearing: -24 };
    const start = { center: HOME.center, zoom: HOME.zoom };
    const merc = (ll: [number, number]) => maplibregl.MercatorCoordinate.fromLngLat(ll);
    const camAt = (t: number) => {
      if (RM) return end;
      const s = ease(c01((t - T.fly[0]) / (T.fly[1] - T.fly[0])));
      const z = lerp(start.zoom, end.zoom, s), k = (1 - Math.pow(2, -(z - start.zoom))) / (1 - Math.pow(2, -(end.zoom - start.zoom)));
      const a = merc(start.center), b = merc(end.center);
      const m = new maplibregl.MercatorCoordinate(lerp(a.x, b.x, k), lerp(a.y, b.y, k));
      const ll = m.toLngLat();
      return { center: [ll.lng, ll.lat] as [number, number], zoom: z, pitch: end.pitch * c01((s - 0.35) / 0.65), bearing: end.bearing * c01((s - 0.25) / 0.75) };
    };
    const hide = (v: 'none' | 'visible') => { for (const id of ['field-casing', 'field-line']) if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', v); };
    const src = (id: string) => map.getSource(id) as GeoJSONSource;
    replaying.current = true; programmatic.current = true;
    live.current.onReplayRunning?.(true); setReplayOn(true);
    map.stop(); hide('none');
    src('cells').setData(fc());
    let raf = 0, done = false, shown = -1, lastFi = -1, lastT = -1, lastRise = -2;
    const t0 = performance.now();
    const finish = (toToday: boolean) => {
      if (done) return;
      done = true; cancelAnimationFrame(raf); replayStop.current = null;
      try { map.removeFeatureState({ source: 'cells' }); } catch { /* source may be gone */ }
      src('outline-draw')?.setData(fc()); hide('visible');
      replaying.current = false; programmatic.current = false;
      setCaption(null); setReplayOn(false); live.current.onReplayRunning?.(false);
      if (toToday) live.current.onReplayT?.(TODAY_T);
      setReplayTick((n) => n + 1);
    };
    replayStop.current = () => finish(false);
    const frame = (t: number) => {
      map.jumpTo({ ...camAt(t), padding: pd });
      const lp = RM ? 1 : ease(c01((t - T.line[0]) / (T.line[1] - T.line[0]))), upto = lp * total, pts: number[][] = [];
      if (lp < 1) { for (let i = 0; i < ring.length; i++) { if (len[i] <= upto) pts.push(ring[i]); else { const f = (upto - len[i - 1]) / ((len[i] - len[i - 1]) || 1); pts.push([lerp(ring[i - 1][0], ring[i][0], f), lerp(ring[i - 1][1], ring[i][1], f)]); break; } } }
      else pts.push(...ring);
      src('outline-draw').setData(fc(pts.length > 1 ? [{ type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: pts } }] : []));
      const fi = t < lapse && !RM ? 0 : frameAtT(t), st = frameStates[fi];
      const rise = (x: { d: number }) => (RM ? 1 : (() => { const k = c01((t - T.rise[0] - x.d * 0.9) / 0.7); return 1 + 2.2 * Math.pow(k - 1, 3) + 1.2 * Math.pow(k - 1, 2); })());
      const startedN = feats.filter((x) => RM || t - T.rise[0] - x.d * 0.9 > 0).length;
      const riseDone = RM || t > T.rise[1] + 0.2;
      if (startedN !== shown) {
        shown = startedN;
        const order = [...feats.keys()].sort((a, b) => feats[a].d - feats[b].d).slice(0, startedN);
        src('cells').setData(fc(order.map((i) => ({ type: 'Feature', geometry: feats[i].f.geometry, properties: { id: feats[i].id, b: base, h: st[i].h, col: st[i].col } }))));
      }
      if (fi !== lastFi || !riseDone || lastRise !== (riseDone ? 1 : 0)) {
        feats.forEach((x, i) => map.setFeatureState({ source: 'cells', id: x.id }, { col: st[i].col, hs: base + (st[i].h - base) * Math.max(0.02, rise(x)) }));
        lastRise = riseDone ? 1 : 0;
      }
      if (fi !== lastFi) {
        lastFi = fi;
        const fr = frames[fi], tq = tOf(fr.year!, (fr.quarter! - 1) * 9 + 4);
        if (tq !== lastT) { lastT = tq; live.current.onReplayT?.(tq); }
        void QN;
      }
      const showCap = t >= lapse - 0.2;
      setCaption((cur) => { const nx = showCap ? captionFor(frames[fi].year!) : null; return (cur?.head ?? '') === (nx?.head ?? '') ? cur : nx; });
      return t >= END;
    };
    if (RM) {
      // reduced motion: no flight or rise; the first quarter shows at once and each press-and-wait steps one quarter
      let i = 0; const stepTo = (j: number) => { frame(keys[j]); };
      stepTo(0);
      const h = setInterval(() => { i++; if (i >= N) { clearInterval(h); finish(true); return; } stepTo(i); }, 900);
      replayStop.current = () => { clearInterval(h); finish(false); };
      return true;
    }
    const loop = (now: number) => { if (done) return; if (frame((now - t0) / 1000)) { finish(true); return; } raf = requestAnimationFrame(loop); };
    raf = requestAnimationFrame(loop);
    return true;
  }

  // ---------- camera ----------
  // camera moves: a smooth in-out so the flight neither lurches off nor stops dead (MapLibre jumps instead under reduced motion)
  const fly = { curve: 1.3, easing: (k: number) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2) };
  const pad = () => ({ left: live.current.leftInset, right: live.current.rightInset, top: 70, bottom: live.current.bottomInset });
  useImperativeHandle(ref, () => ({
    flyToField(loc, mode) {
      const map = mapRef.current!;
      programmatic.current = true;
      const small = loc.area_ha.value < 45;
      if (mode === 'card') map.flyTo({ center: [loc.centroid.lon, loc.centroid.lat], zoom: 10.6, pitch: 0, bearing: 0, padding: pad(), speed: 1.3, ...fly });
      else map.flyTo({ center: [loc.centroid.lon, loc.centroid.lat - (small ? 0.0006 : 0.001)], zoom: (small ? 15.15 : 14.5) - (mode === 'story' ? 0.15 : mode === 'year' ? 0.75 : 0), pitch: mode === 'year' ? 52 : 60, bearing: -24, padding: { ...pad(), right: live.current.rightInset + 330 }, speed: 1.2, ...fly });
    },
    flyHome() { programmatic.current = true; mapRef.current!.flyTo({ ...HOME, padding: { left: 0, right: 0, top: 0, bottom: 0 }, ...fly }); },
    flyTo(lat, lon, zoom) { programmatic.current = true; mapRef.current!.flyTo({ center: [lon, lat], zoom, pitch: 0, bearing: 0, padding: { left: 0, right: 0, top: 0, bottom: 0 }, ...fly }); },
    zoomBy(d) {
      const m = mapRef.current!, sel = live.current.selected;
      const z = Math.min(18, Math.max(3, m.getZoom() + d));
      // zoom controls also drive the explode pitch when the picked field is on screen
      if (sel) {
        const pt = m.project([sel.centroid.lon, sel.centroid.lat]);
        const w = m.getContainer().clientWidth, h = m.getContainer().clientHeight;
        if (pt.x >= -64 && pt.y >= -64 && pt.x <= w + 64 && pt.y <= h + 64) {
          const f = clamp((z - (EXPLODE_Z0 - 0.3)) / (EXPLODE_Z1 - EXPLODE_Z0), 0, 1);
          programmatic.current = true;
          m.easeTo({ zoom: z, pitch: f * 58, bearing: -22 * f, duration: 280 });
          return;
        }
      }
      m.easeTo({ zoom: z, duration: 250 });
    },
    resetNorth() { mapRef.current!.easeTo({ bearing: 0, duration: 300 }); },
    toggle3D() {
      const m = mapRef.current!, sel = live.current.selected;
      if (m.getPitch() > 5) { m.easeTo({ pitch: 0, bearing: 0, duration: 400 }); return; }
      // with a field picked, tilt into the stack at drill zoom so the slabs read as 3D
      if (sel) {
        programmatic.current = true;
        const small = sel.area_ha.value < 45;
        m.easeTo({ center: [sel.centroid.lon, sel.centroid.lat - (small ? 0.0006 : 0.001)], zoom: Math.max(m.getZoom(), small ? 14.8 : 14.2), pitch: 58, bearing: -22, padding: pad(), duration: 500, easing: fly.easing });
        return;
      }
      m.easeTo({ pitch: 58, duration: 400 });
    },
    fitField(loc) {
      const g = loc.mine?.geometry ?? loc.geometry, ring = (g.type === 'Polygon' ? [g.coordinates[0]] : g.coordinates.map((x) => x[0])).flat(), m = mapRef.current!, xs = ring.map((q) => q[0]), ys = ring.map((q) => q[1]);
      programmatic.current = true;
      m.fitBounds([[Math.min(...xs), Math.min(...ys)], [Math.max(...xs), Math.max(...ys)]], { padding: { ...pad(), top: 90, bottom: pad().bottom + 24, right: pad().right + 40, left: pad().left + 40 }, maxZoom: 16.2, pitch: 0, bearing: 0, duration: 900, easing: fly.easing });
    },
    getMap: () => mapRef.current,
    cancelReplay() { replayStop.current?.(); },
    replay(loc) { return startReplay(loc); },
    focusSpot(lat, lon) { const m = mapRef.current!; programmatic.current = true; m.easeTo({ center: [lon, lat], zoom: Math.max(m.getZoom(), 13.2), pitch: 0, bearing: 0, padding: pad(), duration: 900, easing: fly.easing }); },
  }));

  // de-overlap labels vertically, anchored right of the stack
  const sorted = [...labels].sort((a, b) => a.ay - b.ay);
  const lx = Math.min(Math.max(0, ...labels.map((l) => l.ax)) + 34, (el.current?.clientWidth ?? 1440) - p.rightInset - 290);
  let lastY = -1e9;
  const placed = sorted.map((l) => { const y = Math.max(l.ay - 30, lastY + 112); lastY = y; return { ...l, lx, ly: y }; });

  return (
    <div className={`map-wrap zoom-${zoomClass}`}>
      <div ref={el} className="map" />
      {p.reserves && (
        <div className="res-legend" style={{ left: p.leftInset + 16, bottom: p.bottomInset + 14 }} data-testid="reserves-legend">
          <span><i />Reserve boundaries (context)</span>
          <small>For context only. Not part of the analysis.</small>
        </div>
      )}
      {caption && <div className="stack-label replay-cap" style={{ top: 176, left: p.leftInset + (el.current?.clientWidth ?? 1200) / 2 - p.leftInset / 2 }} role="status" aria-live="polite" data-testid="replay-caption"><b>{caption.head}</b><i>{caption.sub}</i></div>}
      {placed.length > 0 && !replayOn && (
        <div className="stack-labels">
          <svg>
            {placed.map((l) => (
              <g key={l.key}>
                <polyline points={`${l.ax},${l.ay} ${l.lx - 12},${l.ly + 30} ${l.lx},${l.ly + 30}`} fill="none" stroke={l.color} strokeWidth="1.5" />
                <circle cx={l.ax} cy={l.ay} r="4" fill={l.color} stroke="#0b1016" strokeWidth="1.5" />
              </g>
            ))}
          </svg>
          {placed.map((l) => (
            <div key={l.key} className="stack-label" style={{ left: l.lx, top: l.ly, borderLeftColor: l.color }}>
              <span className="sl-tag" style={{ color: l.color }}>{l.tag}</span>
              <b>{l.title}</b>
              <span className="sl-val">{l.value}</span>
              <i>{l.note}</i>
            </div>
          ))}
        </div>
      )}
    </div>
  );
});
export default MapView;
