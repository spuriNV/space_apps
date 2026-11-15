// Farm catalog: GET /api/catalog (about 190 real farms, one per place, as tappable pt_ points).
// A light, clustered map layer (separate from the prepared fields) and the data the pick list group reads.
import type maplibregl from 'maplibre-gl';
import { API_BASE } from '../../api';

export interface CatalogItem {
  id: string; name: string; lat: number; lon: number; region: 'ca' | 'bc'; area: string;
  crop_group: string; crop_group_label: string; county: string; acres: number | null;
  land_status?: string | { kind?: string; name?: string; nation?: string } | null;
}
export interface Catalog { count: number; total: number; items: CatalogItem[]; crop_groups: Record<string, { label: string; count: number }> }

let cached: Promise<Catalog | null> | null = null;
/** One fetch per session (the API caches it for an hour). null when the API does not have it. */
export function getCatalog(): Promise<Catalog | null> {
  cached ??= fetch(`${API_BASE}/catalog`).then((r) => (r.ok ? r.json() : null)).then((b) => (b && Array.isArray(b.items) ? (b as Catalog) : null)).catch(() => null);
  return cached;
}

/** Muted tones that read on satellite imagery (each pin also has a paper ring). */
export const GROUP_COLOR: Record<string, string> = {
  grapes: '#7a4b86', forage: '#4f8f3a', vegetables: '#d2692c', nuts: '#9a6a3a', grain: '#d9a53a',
  rice: '#3d7fc4', citrus: '#e48a1c', cotton: '#c9c4b4', orchard: '#b8465a', canola: '#e3d24a',
};
export const groupColor = (g: string) => GROUP_COLOR[g] ?? '#8a8a80';
export const landNote = (l: CatalogItem['land_status']) => {
  const kind = typeof l === 'string' ? l : l?.kind;
  return kind && /reserve|reservation|trust|tribal/i.test(kind) ? 'On reserve or tribal land' : '';
};

const SRC = 'catalog';
const empty = { type: 'FeatureCollection', features: [] } as GeoJSON.FeatureCollection;
/** Add the clustered source and its layers (call once on map load, before the field layers so it stays underneath). */
export function addCatalogLayers(map: maplibregl.Map, onPick: (it: { id: string; lat: number; lon: number }) => void) {
  map.addSource(SRC, { type: 'geojson', data: empty, cluster: true, clusterRadius: 40, clusterMaxZoom: 11 });
  map.addLayer({ id: 'cat-cluster', type: 'circle', source: SRC, filter: ['has', 'point_count'], paint: {
    'circle-color': '#f7f6f0', 'circle-opacity': 0.92, 'circle-stroke-color': '#191c16', 'circle-stroke-width': 1,
    'circle-radius': ['step', ['get', 'point_count'], 13, 10, 16, 30, 20] } });
  map.addLayer({ id: 'cat-count', type: 'symbol', source: SRC, filter: ['has', 'point_count'], layout: { 'text-field': ['get', 'point_count_abbreviated'], 'text-font': ['Noto Sans Bold'], 'text-size': 13, 'text-allow-overlap': true }, paint: { 'text-color': '#191c16' } });
  map.addLayer({ id: 'cat-pt', type: 'circle', source: SRC, filter: ['!', ['has', 'point_count']], paint: {
    'circle-color': ['get', 'color'], 'circle-radius': ['interpolate', ['linear'], ['zoom'], 5, 5, 12, 8], 'circle-stroke-color': '#f7f6f0', 'circle-stroke-width': 1.75, 'circle-opacity': 0.95 } });
  map.on('click', 'cat-cluster', async (e) => {
    const f = e.features?.[0]; if (!f) return;
    const src = map.getSource(SRC) as maplibregl.GeoJSONSource;
    const z = await src.getClusterExpansionZoom(f.properties!.cluster_id);
    map.easeTo({ center: (f.geometry as GeoJSON.Point).coordinates as [number, number], zoom: z + 0.5 });
  });
  map.on('click', 'cat-pt', (e) => {
    const f = e.features?.[0]; if (!f) return;
    const [lon, lat] = (f.geometry as GeoJSON.Point).coordinates;
    onPick({ id: String(f.properties!.id), lat, lon });
  });
  for (const l of ['cat-cluster', 'cat-pt']) {
    map.on('mouseenter', l, () => (map.getCanvas().style.cursor = 'pointer'));
    map.on('mouseleave', l, () => (map.getCanvas().style.cursor = ''));
  }
}
export function setCatalogData(map: maplibregl.Map, items: CatalogItem[], group: string | null) {
  const src = map.getSource(SRC) as maplibregl.GeoJSONSource | undefined;
  src?.setData({ type: 'FeatureCollection', features: items.filter((i) => !group || i.crop_group === group).map((i) => ({
    type: 'Feature', properties: { id: i.id, color: groupColor(i.crop_group) }, geometry: { type: 'Point', coordinates: [i.lon, i.lat] } })) });
}
