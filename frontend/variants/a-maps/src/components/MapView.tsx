import { useEffect, useRef } from 'react';
import maplibregl, { type Map as MLMap, type GeoJSONSource } from 'maplibre-gl';
import { getBcCard, getFieldYear, getLocations, getTrends, getZones } from '../api';
import type { LocationId, MeasureKey, TrendLayer } from '../types';
import { COVER_COLORS, RAMPS, clamp, ramp, smoothstep } from '../util';

export type Selected = LocationId | 'bc' | null;
export interface CameraInfo { zoom: number; pitch: number; bearing: number; nearId: LocationId | null; drill: number }
export interface ReplayState { on: boolean; year: number; week: number }

interface Props {
  selected: Selected;
  basemap: 'streets' | 'satellite';
  trendLayer: TrendLayer | null;
  measure: MeasureKey;
  replay: ReplayState;
  tilt3d: boolean;
  footprints: boolean;
  onSelect: (id: Selected) => void;
  onCamera: (c: CameraInfo) => void;
  onReady: (map: MLMap) => void;
}

const STREETS = 'https://tiles.openfreemap.org/styles/liberty';
const ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
export const CA_VIEW = { center: [-119.6, 37.55] as [number, number], zoom: 5.75 };
const DRILL_START = 13.6; // zoom where cells start to rise and the camera starts to pitch
const DRILL_FULL = 15.2;
const MAX_PITCH = 58;
const H_MAX = 150; // metres of extrusion for the top of the scale
const LABELS_BEFORE = 'waterway_line_label';

const LOCS = getLocations();
const ZONES = Object.fromEntries(LOCS.map((l) => [l.id, getZones(l.id)]));
const DOMAINS = Object.fromEntries(
  LOCS.map((l) => {
    const f = ZONES[l.id].cells.features.map((c) => c.properties);
    const mm = (k: 'et_mm' | 'bare_days') => [Math.min(...f.map((p) => p[k])), Math.max(...f.map((p) => p[k]))];
    return [l.id, { ndvi: [0.2, 0.92], et_mm: mm('et_mm'), stress: [0, 1], bare_days: mm('bare_days') }];
  }),
) as Record<LocationId, Record<MeasureKey, number[]>>;
export const measureDomain = (id: LocationId, m: MeasureKey) => DOMAINS[id][m];

function distM(a: { lng: number; lat: number }, b: { lon: number; lat: number }) {
  const kx = 111320 * Math.cos((b.lat * Math.PI) / 180);
  return Math.hypot((a.lng - b.lon) * kx, (a.lat - b.lat) * 111320);
}
function nearest(center: { lng: number; lat: number }) {
  let best: { id: LocationId; d: number } | null = null;
  for (const l of LOCS) {
    const d = distM(center, l.centroid);
    if (!best || d < best.d) best = { id: l.id, d };
  }
  return best!;
}

/** Build the cell FeatureCollection with colour + height for the active measure or replay week. */
function cellData(measure: MeasureKey, replay: ReplayState, selected: Selected) {
  const feats: GeoJSON.Feature[] = [];
  for (const l of LOCS) {
    const z = ZONES[l.id];
    const rp = replay.on && selected === l.id ? getFieldYear(l.id).years.find((y) => y.year === replay.year) : null;
    const w0 = Math.floor(replay.week), w1 = Math.min(51, w0 + 1), f = replay.week - w0;
    for (const c of z.cells.features) {
      const p = c.properties;
      let t: number, col: string, label: string;
      if (rp) {
        const cls = rp.rule[w0];
        const n = rp.ndvi[w0] * (1 - f) + rp.ndvi[w1] * f;
        const cell = clamp(n * (1 + 0.22 * p.v) + (n > 0.3 ? 0.04 * p.v : 0), 0.02, 0.93);
        if (cls === 'w') { t = 0.03; col = COVER_COLORS.w; label = 'water'; }
        else { t = clamp((cell - 0.05) / 0.87, 0, 1); col = ramp(RAMPS.ndvi, clamp((cell - 0.1) / 0.8, 0, 1)); label = `NDVI ${cell.toFixed(2)}`; }
      } else {
        const [lo, hi] = DOMAINS[l.id][measure];
        const v = p[measure];
        t = clamp((v - lo) / (hi - lo || 1), 0, 1);
        col = ramp(RAMPS[measure], t);
        label = measure === 'ndvi' ? `NDVI ${v.toFixed(2)}` : measure === 'et_mm' ? `${v} mm (${(v / 25.4).toFixed(1)} in) per season` : measure === 'stress' ? `stress score ${v.toFixed(2)}` : `${v} bare days / yr`;
      }
      feats.push({ type: 'Feature', id: c.id, geometry: c.geometry, properties: { loc: l.id, col, h: 6 + t * H_MAX, label, i: p.i, j: p.j } });
    }
  }
  return { type: 'FeatureCollection', features: feats } as GeoJSON.FeatureCollection;
}

function pinEl(kind: 'field' | 'bc', label: string, sub: string) {
  const el = document.createElement('div');
  el.className = `pin pin-${kind}`;
  el.innerHTML = `
    <svg class="pin-svg" width="27" height="38" viewBox="0 0 27 38">
      <path d="M13.5 0C6 0 0 6 0 13.500c0 9.600 12 22.500 12.600 23.800a1.200 1.200 0 0 0 1.800 0C15 36 27 23.100 27 13.500 27 6 21 0 13.500 0z" fill="${kind === 'bc' ? '#5f6368' : '#ea4335'}" stroke="${kind === 'bc' ? '#3c4043' : '#b31412'}" stroke-width="1"/>
      ${kind === 'bc' ? '<text x="13.5" y="19" text-anchor="middle" font-size="15" font-weight="700" fill="#fff" font-family="Roboto, Arial">i</text>' : '<circle cx="13.5" cy="13.5" r="5" fill="#b31412"/>'}
    </svg>
    <div class="pin-label"><span class="pin-name">${label}</span><span class="pin-sub">${sub}</span></div>`;
  return el;
}

export default function MapView(props: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const readyRef = useRef(false);
  const p = useRef(props);
  p.current = props;
  const pins = useRef<Record<string, HTMLElement>>({});
  const origLabel = useRef<Record<string, { c: unknown; h: unknown }>>({});

  // ---------------------------------------------------------------- init
  useEffect(() => {
    const map = new maplibregl.Map({
      container: ref.current!,
      style: STREETS,
      center: CA_VIEW.center,
      zoom: CA_VIEW.zoom,
      maxPitch: 70,
      attributionControl: false,
      canvasContextAttributes: { preserveDrawingBuffer: true, antialias: true },
    });
    mapRef.current = map;
    (window as unknown as { __map: MLMap }).__map = map;
    map.addControl(new maplibregl.AttributionControl({ compact: false, customAttribution: 'Imagery © Esri, Maxar, Earthstar Geographics' }), 'bottom-right');
    map.addControl(new maplibregl.ScaleControl({ unit: 'metric', maxWidth: 90 }), 'bottom-right');

    // Scroll-in drill-down: near a field, camera pitch is a function of zoom.
    map.transformCameraUpdate = (next) => {
      const cur = p.current;
      if (next.zoom < 12.6) return {};
      if (nearest(next.center).d > 2600) return {};
      if (!cur.tilt3d) return { pitch: 0 };
      return { pitch: MAX_PITCH * smoothstep(DRILL_START, DRILL_FULL, next.zoom) };
    };

    // pins
    for (const l of LOCS) {
      const el = pinEl('field', l.short_name, 'Example field');
      el.addEventListener('click', (e) => { e.stopPropagation(); p.current.onSelect(l.id); });
      pins.current[l.id] = el;
      new maplibregl.Marker({ element: el, anchor: 'bottom', offset: [0, 2] }).setLngLat([l.centroid.lon, l.centroid.lat]).addTo(map);
    }
    const bc = getBcCard();
    const bel = pinEl('bc', 'Why not BC yet', 'Not modelled');
    bel.addEventListener('click', (e) => { e.stopPropagation(); p.current.onSelect('bc'); });
    pins.current.bc = bel;
    new maplibregl.Marker({ element: bel, anchor: 'bottom', offset: [0, 2] }).setLngLat([bc.centroid.lon, bc.centroid.lat]).addTo(map);

    map.on('load', () => {
      const firstRoad = map.getLayer('road_area_pattern') ? 'road_area_pattern' : LABELS_BEFORE;
      map.addSource('esri', { type: 'raster', tiles: [ESRI], tileSize: 256, maxzoom: 18 });
      map.addLayer({ id: 'sat', type: 'raster', source: 'esri', layout: { visibility: 'none' }, paint: { 'raster-fade-duration': 0 } }, firstRoad);

      map.addSource('trend', { type: 'geojson', data: { type: 'FeatureCollection', features: LOCS.flatMap((l) => getTrends(l.id).cells.features) } });
      map.addLayer({ id: 'trend-fill', type: 'fill', source: 'trend', layout: { visibility: 'none' }, paint: { 'fill-color': '#ccc', 'fill-opacity': 0.62 } }, LABELS_BEFORE);
      map.addLayer({ id: 'trend-line', type: 'line', source: 'trend', layout: { visibility: 'none' }, paint: { 'line-color': '#fff', 'line-width': 0.6, 'line-opacity': 0.7 } }, LABELS_BEFORE);

      map.addSource('smap', { type: 'geojson', data: { type: 'FeatureCollection', features: LOCS.map((l) => ({ type: 'Feature', properties: { loc: l.id }, geometry: ZONES[l.id].footprints.smap_9km.geometry })) } });
      map.addLayer({ id: 'smap-fill', type: 'fill', source: 'smap', minzoom: 8, paint: { 'fill-color': '#1a73e8', 'fill-opacity': 0.05 } }, LABELS_BEFORE);
      map.addLayer({ id: 'smap-line', type: 'line', source: 'smap', minzoom: 8, paint: { 'line-color': '#1a73e8', 'line-width': 2, 'line-dasharray': [3, 2] } }, LABELS_BEFORE);
      map.addLayer({ id: 'smap-label', type: 'symbol', source: 'smap', minzoom: 9.5, layout: { 'symbol-placement': 'line', 'text-field': 'One SMAP soil-moisture pixel · 9 km', 'text-font': ['Noto Sans Bold'], 'text-size': 12, 'text-offset': [0, -0.9], 'symbol-spacing': 420, 'text-keep-upright': true }, paint: { 'text-color': '#174ea6', 'text-halo-color': '#fff', 'text-halo-width': 2 } });

      map.addSource('modis', { type: 'geojson', data: { type: 'FeatureCollection', features: LOCS.map((l) => ({ type: 'Feature', properties: { loc: l.id }, geometry: ZONES[l.id].footprints.modis_250m.geometry })) } });
      map.addLayer({ id: 'modis-fill', type: 'fill', source: 'modis', minzoom: 12.8, paint: { 'fill-color': '#f29900', 'fill-opacity': 0.12 } }, LABELS_BEFORE);
      map.addLayer({ id: 'modis-line', type: 'line', source: 'modis', minzoom: 12.8, paint: { 'line-color': '#e37400', 'line-width': 2.5 } }, LABELS_BEFORE);
      map.addLayer({ id: 'modis-label', type: 'symbol', source: 'modis', minzoom: 13.4, layout: { 'text-field': 'One MODIS\npixel · 250 m', 'text-font': ['Noto Sans Bold'], 'text-size': 12, 'text-allow-overlap': true }, paint: { 'text-color': '#b06000', 'text-halo-color': '#fff', 'text-halo-width': 2 } });

      map.addSource('fields', { type: 'geojson', data: { type: 'FeatureCollection', features: LOCS.map((l) => ({ type: 'Feature', properties: { id: l.id }, geometry: l.geometry })) } });
      map.addLayer({ id: 'field-fill', type: 'fill', source: 'fields', paint: { 'fill-color': '#34a853', 'fill-opacity': ['interpolate', ['linear'], ['zoom'], 12.4, 0.45, 13.2, 0.08] } }, LABELS_BEFORE);
      map.addLayer({ id: 'field-line', type: 'line', source: 'fields', paint: { 'line-color': '#188038', 'line-width': ['interpolate', ['linear'], ['zoom'], 8, 1.5, 13, 3] } }, LABELS_BEFORE);

      map.addSource('cells', { type: 'geojson', data: cellData(p.current.measure, p.current.replay, p.current.selected) });
      map.addLayer({
        id: 'cells', type: 'fill-extrusion', source: 'cells', minzoom: 12.4,
        paint: {
          'fill-extrusion-color': ['get', 'col'],
          'fill-extrusion-height': ['interpolate', ['linear'], ['zoom'], DRILL_START, 0, DRILL_FULL, ['get', 'h']],
          'fill-extrusion-opacity': ['interpolate', ['linear'], ['zoom'], 12.4, 0, 13.1, 0.96],
          'fill-extrusion-vertical-gradient': true,
        },
      }, LABELS_BEFORE);
      map.setLight({ anchor: 'viewport', color: '#ffffff', intensity: 0.38, position: [1.4, 215, 40] });

      // interactions
      const hover = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 14, className: 'cell-tip' });
      map.on('click', 'field-fill', (e) => p.current.onSelect(e.features![0].properties.id));
      map.on('click', 'cells', (e) => p.current.onSelect(e.features![0].properties.loc));
      for (const id of ['field-fill', 'cells']) {
        map.on('mouseenter', id, () => { map.getCanvas().style.cursor = 'pointer'; });
        map.on('mouseleave', id, () => { map.getCanvas().style.cursor = ''; hover.remove(); });
      }
      map.on('mousemove', 'cells', (e) => {
        if (map.getZoom() < 14) return;
        const f = e.features![0].properties;
        hover.setLngLat(e.lngLat).setHTML(`<b>${f.label}</b><span>30 m cell · row ${f.j + 1}, col ${f.i + 1}</span>`).addTo(map);
      });

      readyRef.current = true;
      syncAll();
      p.current.onReady(map);
    });

    let raf = 0;
    const report = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const z = map.getZoom();
        const n = nearest(map.getCenter());
        const near = n.d < 2600;
        p.current.onCamera({ zoom: Math.round(z * 10) / 10, pitch: Math.round(map.getPitch()), bearing: Math.round(map.getBearing()), nearId: near ? n.id : null, drill: near ? Math.round(smoothstep(DRILL_START, DRILL_FULL, z) * 20) / 20 : 0 });
        for (const el of Object.values(pins.current)) el.classList.toggle('pin-compact', z > 12.9);
      });
    };
    map.on('move', report);
    map.on('load', report);
    return () => { cancelAnimationFrame(raf); map.remove(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---------------------------------------------------------------- sync helpers
  function syncBasemap() {
    const map = mapRef.current!;
    const sat = p.current.basemap === 'satellite';
    map.setLayoutProperty('sat', 'visibility', sat ? 'visible' : 'none');
    for (const l of map.getStyle().layers) {
      if (l.type === 'symbol' && !['smap-label', 'modis-label'].includes(l.id) && l.layout?.['text-field']) {
        if (!origLabel.current[l.id]) origLabel.current[l.id] = { c: map.getPaintProperty(l.id, 'text-color'), h: map.getPaintProperty(l.id, 'text-halo-color') };
        map.setPaintProperty(l.id, 'text-color', sat ? '#ffffff' : origLabel.current[l.id].c);
        map.setPaintProperty(l.id, 'text-halo-color', sat ? 'rgba(0,0,0,0.75)' : origLabel.current[l.id].h);
      }
      if (l.type === 'line' && /^(road|bridge)_/.test(l.id)) map.setPaintProperty(l.id, 'line-opacity', sat ? 0.45 : 1);
    }
    map.setPaintProperty('field-line', 'line-color', sat ? '#ffffff' : '#188038');
  }
  function syncTrend() {
    const map = mapRef.current!;
    const t = p.current.trendLayer;
    for (const id of ['trend-fill', 'trend-line']) map.setLayoutProperty(id, 'visibility', t ? 'visible' : 'none');
    if (t) {
      const dom = getTrends('car_colusa_rice').layers[t].domain;
      const stops = RAMPS[t].flatMap(([s, c]) => [dom[0] + s * (dom[1] - dom[0]), c]);
      map.setPaintProperty('trend-fill', 'fill-color', ['interpolate', ['linear'], ['get', t], ...stops] as never);
    }
  }
  function syncSelection() {
    const map = mapRef.current!;
    const sel = p.current.selected;
    const selField = sel && sel !== 'bc' ? sel : '';
    map.setPaintProperty('field-line', 'line-color', ['case', ['==', ['get', 'id'], selField], '#1a73e8', p.current.basemap === 'satellite' ? '#ffffff' : '#188038']);
    const fp = p.current.footprints && !!selField;
    for (const id of ['smap-fill', 'smap-line', 'smap-label']) { map.setLayoutProperty(id, 'visibility', fp ? 'visible' : 'none'); map.setFilter(id, ['==', ['get', 'loc'], selField]); }
    for (const id of ['modis-fill', 'modis-line', 'modis-label']) map.setLayoutProperty(id, 'visibility', p.current.footprints ? 'visible' : 'none');
    for (const [id, el] of Object.entries(pins.current)) el.classList.toggle('pin-selected', id === sel);
  }
  function syncCells() {
    const map = mapRef.current!;
    (map.getSource('cells') as GeoJSONSource).setData(cellData(p.current.measure, p.current.replay, p.current.selected));
  }
  function syncTilt() {
    const map = mapRef.current!;
    map.setPaintProperty('cells', 'fill-extrusion-height', p.current.tilt3d ? ['interpolate', ['linear'], ['zoom'], DRILL_START, 0, DRILL_FULL, ['get', 'h']] : 0);
    map.easeTo({ zoom: map.getZoom(), duration: 500 }); // re-run transformCameraUpdate so pitch follows the mode
  }
  function syncAll() { syncBasemap(); syncTrend(); syncSelection(); syncCells(); }

  useEffect(() => { if (readyRef.current) { syncBasemap(); syncSelection(); } }, [props.basemap]);
  useEffect(() => { if (readyRef.current) syncTrend(); }, [props.trendLayer]);
  useEffect(() => { if (readyRef.current) syncSelection(); }, [props.selected, props.footprints]);
  useEffect(() => { if (readyRef.current) syncCells(); }, [props.measure, props.replay.on, props.replay.year, props.replay.week, props.selected]);
  useEffect(() => { if (readyRef.current) syncTilt(); }, [props.tilt3d]);

  // camera: selection
  const prevSel = useRef<Selected>(null);
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const sel = props.selected;
    if (prevSel.current === sel) return;
    prevSel.current = sel;
    const go = () => {
      map.resize();
      if (sel === 'bc') {
        const c = getBcCard().centroid;
        map.flyTo({ center: [c.lon, c.lat], zoom: 7.4, pitch: 0, bearing: 0, duration: 1800 });
      } else if (sel) {
        const loc = LOCS.find((l) => l.id === sel)!;
        const far = distM(map.getCenter(), loc.centroid) > 6000 || map.getZoom() < 11.5;
        if (far) {
          const ring = ZONES[sel].footprints.smap_9km.geometry.coordinates[0];
          const b = new maplibregl.LngLatBounds(ring[0] as [number, number], ring[2] as [number, number]);
          map.fitBounds(b, { padding: { left: 56, top: 96, right: 72, bottom: 72 }, bearing: 0, pitch: 0, duration: 2200 });
        }
      }
    };
    if (readyRef.current) go(); else map.once('load', go);
  }, [props.selected]);

  return <div ref={ref} className="map" />;
}

export function flyToDrill(map: MLMap, id: LocationId) {
  const loc = LOCS.find((l) => l.id === id)!;
  map.flyTo({ center: [loc.centroid.lon, loc.centroid.lat], zoom: 15.25, bearing: -22, duration: 2600 });
}
export function flyHome(map: MLMap) {
  map.flyTo({ ...CA_VIEW, pitch: 0, bearing: 0, duration: 1800 });
}
