import { useEffect, useRef, useState } from 'react';
import maplibregl, { type GeoJSONSource, type Map as MlMap } from 'maplibre-gl';
import { getCells, getLocations } from './api';
import { MEASURES, type MeasureKey } from './measures';
import type { CellProps, Location } from './types';

const STREETS = 'https://tiles.openfreemap.org/styles/liberty';
const ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
const CA_BOUNDS: [[number, number], [number, number]] = [[-124.6, 32.4], [-113.9, 42.1]];
export const ZOOM_3D_IN = 15;
const ZOOM_3D_OUT = 14.4;
const SEL = '#ff2d95';

export interface MapProps {
  loc: Location | null; hoverId: string | null; is3d: boolean; measure: MeasureKey; basemap: 'map' | 'satellite'; selectedCell: number | null;
  onHover: (id: string | null) => void; onOpen: (id: string) => void; onVisible: (ids: string[]) => void; onSet3d: (v: boolean) => void; onSelectCell: (c: CellProps | null) => void; onZoom: (z: number) => void;
}

function measurePaint(k: MeasureKey) {
  const m = MEASURES[k];
  const get = ['get', m.prop as string];
  const ramp = ['interpolate', ['linear'], get, ...m.stops.flatMap(([v, c]) => [v, c])];
  return {
    color: ['case', ['boolean', ['feature-state', 'sel'], false], SEL, ramp] as unknown as maplibregl.ExpressionSpecification,
    height: ['interpolate', ['linear'], get, m.domain[0], 6, m.domain[1], 95] as unknown as maplibregl.ExpressionSpecification,
  };
}

export default function MapView(p: MapProps) {
  const el = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const markers = useRef<Record<string, { m: maplibregl.Marker; el: HTMLElement }>>({});
  const props = useRef(p);
  props.current = p;
  const [ready, setReady] = useState(false);
  const selRef = useRef<number | null>(null);

  useEffect(() => {
    const map = new maplibregl.Map({
      container: el.current!, style: STREETS, bounds: CA_BOUNDS, fitBoundsOptions: { padding: 48 }, maxPitch: 72,
      attributionControl: false, // added below as compact
    });
    mapRef.current = map;
    (window as unknown as { __map: MlMap }).__map = map;
    map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'bottom-right');
    map.addControl(new maplibregl.ScaleControl({ unit: 'imperial' }), 'bottom-left');

    map.on('load', () => {
      const firstSymbol = map.getStyle().layers.find((l) => l.type === 'symbol')?.id;
      map.addSource('esri', { type: 'raster', tiles: [ESRI], tileSize: 256, maxzoom: 18, attribution: 'Imagery © Esri, Maxar, Earthstar Geographics' });
      map.addLayer({ id: 'sat', type: 'raster', source: 'esri', layout: { visibility: 'none' } }, firstSymbol);

      const locs = getLocations();
      map.addSource('fields', { type: 'geojson', data: { type: 'FeatureCollection', features: locs.map((l) => ({ type: 'Feature', properties: { id: l.id, name: l.short_name }, geometry: l.geometry })) } });
      map.addSource('smap', { type: 'geojson', data: { type: 'FeatureCollection', features: locs.map((l) => ({ type: 'Feature', properties: { id: l.id, label: 'SMAP soil-moisture cell · 9 km' }, geometry: l.regional_cell.footprint })) } });
      map.addSource('cells', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });

      map.addLayer({ id: 'smap-fill', type: 'fill', source: 'smap', minzoom: 9, paint: { 'fill-color': '#1a73e8', 'fill-opacity': 0.05 } });
      map.addLayer({ id: 'smap-line', type: 'line', source: 'smap', minzoom: 9, paint: { 'line-color': '#1a73e8', 'line-width': 1.6, 'line-dasharray': [3, 2.5] } });
      map.addLayer({ id: 'smap-label', type: 'symbol', source: 'smap', minzoom: 10, layout: { 'symbol-placement': 'line', 'text-field': ['get', 'label'], 'text-font': ['Noto Sans Bold'], 'text-size': 11.5, 'text-offset': [0, -0.9], 'symbol-spacing': 420 }, paint: { 'text-color': '#174ea6', 'text-halo-color': '#fff', 'text-halo-width': 1.6 } });
      map.addLayer({ id: 'field-fill', type: 'fill', source: 'fields', minzoom: 8, paint: { 'fill-color': '#188038', 'fill-opacity': 0.22 } });
      map.addLayer({ id: 'field-casing', type: 'line', source: 'fields', minzoom: 8, paint: { 'line-color': '#ffffff', 'line-width': 5 } });
      map.addLayer({ id: 'field-line', type: 'line', source: 'fields', minzoom: 8, paint: { 'line-color': '#188038', 'line-width': 2.5 } });
      const mp = measurePaint('ndvi');
      map.addLayer({
        id: 'cells-3d', type: 'fill-extrusion', source: 'cells', layout: { visibility: 'none' },
        paint: { 'fill-extrusion-color': mp.color, 'fill-extrusion-height': mp.height, 'fill-extrusion-base': 0, 'fill-extrusion-opacity': 0.96, 'fill-extrusion-vertical-gradient': true },
      });

      map.on('click', 'cells-3d', (e) => {
        const f = e.features?.[0];
        if (f) props.current.onSelectCell(f.properties as CellProps);
      });
      map.on('mouseenter', 'cells-3d', () => (map.getCanvas().style.cursor = 'pointer'));
      map.on('mouseleave', 'cells-3d', () => (map.getCanvas().style.cursor = ''));
      map.on('click', 'field-fill', (e) => {
        const id = e.features?.[0]?.properties?.id as string | undefined;
        if (id && props.current.loc?.id !== id) props.current.onOpen(id);
      });

      // Listing-style pill markers, one per example field
      locs.forEach((l) => {
        const node = document.createElement('button');
        node.className = 'pinpill';
        node.dataset.loc = l.id;
        node.innerHTML = `<span class="pin-dot"></span><b>${l.short_name}</b><small>${Math.round(l.area_ha.value)} ha</small>`;
        node.addEventListener('mouseenter', () => props.current.onHover(l.id));
        node.addEventListener('mouseleave', () => props.current.onHover(null));
        node.addEventListener('click', (ev) => { ev.stopPropagation(); props.current.onOpen(l.id); });
        const m = new maplibregl.Marker({ element: node, anchor: 'bottom', offset: [0, -6] }).setLngLat([l.centroid.lon, l.centroid.lat]).addTo(map);
        markers.current[l.id] = { m, el: node };
      });

      const report = () => {
        const b = map.getBounds();
        props.current.onVisible(locs.filter((l) => b.contains([l.centroid.lon, l.centroid.lat])).map((l) => l.id));
        props.current.onZoom(map.getZoom());
      };
      map.on('moveend', report);
      report();

      // Scroll-in drill-down: past the threshold the field becomes a 3D block; scroll out to leave
      map.on('zoomend', () => {
        const { loc, is3d, onSet3d } = props.current;
        const z = map.getZoom();
        if (loc && !is3d && z >= ZOOM_3D_IN) onSet3d(true);
        else if (is3d && z < ZOOM_3D_OUT) onSet3d(false);
      });
      setReady(true);
    });
    const ro = new ResizeObserver(() => map.resize());
    ro.observe(el.current!);
    return () => { ro.disconnect(); Object.values(markers.current).forEach((x) => x.m.remove()); markers.current = {}; map.remove(); mapRef.current = null; };
  }, []);

  // camera + data follow the opened field
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    if (!p.loc) {
      map.fitBounds(CA_BOUNDS, { padding: 48, pitch: 0, bearing: 0, duration: 900 });
    } else {
      (map.getSource('cells') as GeoJSONSource).setData(getCells(p.loc.id) as unknown as GeoJSON.FeatureCollection);
      selRef.current = null;
      map.flyTo({ center: [p.loc.centroid.lon, p.loc.centroid.lat], zoom: 13.6, pitch: 0, bearing: 0, duration: 1400 });
    }
    Object.entries(markers.current).forEach(([id, x]) => x.el.classList.toggle('opened', p.loc?.id === id));
  }, [ready, p.loc?.id]);

  // 3D on/off
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    map.setLayoutProperty('cells-3d', 'visibility', p.is3d ? 'visible' : 'none');
    map.setPaintProperty('field-fill', 'fill-opacity', p.is3d ? 0 : 0.22);
    el.current!.classList.toggle('is3d', p.is3d);
    if (p.is3d && p.loc) {
      map.easeTo({ center: [p.loc.centroid.lon, p.loc.centroid.lat], zoom: Math.max(map.getZoom(), 15.25), pitch: 58, bearing: -22, padding: { top: 0, left: 0, right: 0, bottom: 190 }, duration: 1100 });
    } else if (!p.is3d) {
      map.easeTo({ pitch: 0, bearing: 0, padding: { top: 0, left: 0, right: 0, bottom: 0 }, zoom: p.loc ? Math.min(map.getZoom(), 14.2) : map.getZoom(), duration: 800 });
    }
  }, [ready, p.is3d]);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    const mp = measurePaint(p.measure);
    map.setPaintProperty('cells-3d', 'fill-extrusion-color', mp.color);
    map.setPaintProperty('cells-3d', 'fill-extrusion-height', mp.height);
  }, [ready, p.measure]);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    map.setLayoutProperty('sat', 'visibility', p.basemap === 'satellite' ? 'visible' : 'none');
  }, [ready, p.basemap]);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    if (selRef.current != null) map.setFeatureState({ source: 'cells', id: selRef.current }, { sel: false });
    if (p.selectedCell != null) map.setFeatureState({ source: 'cells', id: p.selectedCell }, { sel: true });
    selRef.current = p.selectedCell;
  }, [ready, p.selectedCell, p.loc?.id]);

  useEffect(() => {
    Object.entries(markers.current).forEach(([id, x]) => x.el.classList.toggle('hover', p.hoverId === id));
  }, [p.hoverId, ready]);

  return <div ref={el} className="map" />;
}
