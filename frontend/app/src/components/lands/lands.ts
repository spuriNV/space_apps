// First Nations lands (reserves and tribal lands): types and helpers shared by the map layer, the list and the Nation panel.
// Data: GET /api/lands (backend/nation/fetch_lands.py). Boundaries are legal or statistical lines, not traditional territory.
import { t, locale } from '../../i18n';
export interface LandProps {
  id: string; name: string; nation: string; kind: 'reserve' | 'reservation' | 'trust'; area_ha: number;
  band_number?: string; province?: 'BC'; state?: 'CA'; centroid: [number, number];
}
export type LandFeature = GeoJSON.Feature<GeoJSON.Polygon | GeoJSON.MultiPolygon, LandProps>;
export interface LandDetail {
  id: string; name: string; nation: string; kind: string; kind_label: string; jurisdiction: 'BC' | 'CA'; area_ha: number; area_acres: number;
  centroid: { lon: number; lat: number }; location_id: string; website: string | null; caveat: string;
  nearby: { id: string; name: string; kind: 'catalog farm' | 'prepared field'; lat: number; lon: number; crop?: string | null; acres?: number | null; distance_km: number }[];
  nearby_radius_km: number; source?: { title: string; url: string } | null;
}
export const regionOf = (p: LandProps) => (p.province === 'BC' ? 'BC' : 'CA') as 'BC' | 'CA';
export const regionName = (r: 'BC' | 'CA') => (r === 'BC' ? t('land.bc') : t('land.ca'));
export const kindLabel = (k: string) => (k === 'reserve' ? t('land.reserve') : t('land.tribal'));
const fmt = (n: number) => Math.round(n).toLocaleString(locale);
/** "1,583 acres (641 ha)"; small lands show one decimal. */
export function areaText(ha: number) {
  const ac = ha * 2.47105;
  return t('land.area', { ac: ac < 100 ? ac.toFixed(1) : fmt(ac), ha: ha < 100 ? ha.toFixed(1) : fmt(ha) });
}
export function boundsOf(f: LandFeature): [[number, number], [number, number]] {
  let w = 180, s = 90, e = -180, n = -90;
  const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
  for (const poly of polys) for (const [x, y] of poly[0]) { w = Math.min(w, x); e = Math.max(e, x); s = Math.min(s, y); n = Math.max(n, y); }
  return [[w, s], [e, n]];
}
