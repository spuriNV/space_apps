// First Nations lands (reserves and tribal lands): types and helpers shared by the map layer, the list and the Nation panel.
// Data: GET /api/lands (backend/nation/fetch_lands.py). Boundaries are legal or statistical lines, not traditional territory.
export interface LandProps {
  id: string; name: string; nation: string; kind: 'reserve' | 'reservation' | 'trust' | 'other'; area_ha: number;
  band_number?: string; country: 'US' | 'CAN'; province?: string; state?: string; centroid: [number, number]; bbox?: [number, number, number, number];
}
/** Polygon or MultiPolygon from the viewport route; a Point (at the centroid) from the light overview the list and the zoomed-out map use. */
export type LandFeature = GeoJSON.Feature<GeoJSON.Polygon | GeoJSON.MultiPolygon | GeoJSON.Point, LandProps>;
const KINDS = ['reserve', 'reservation', 'trust', 'other'] as const;
/** GET /api/lands/overview rows -> point features (one per land, no outlines). */
export function fromOverview(b: { rows: (string | number)[][] }): LandFeature[] {
  return b.rows.map((r) => {
    const country = r[5] as 'US' | 'CAN', reg = r[6] as string;
    return { type: 'Feature', geometry: { type: 'Point', coordinates: [r[7] as number, r[8] as number] }, properties: {
      id: r[0] as string, name: r[1] as string, nation: r[2] as string, kind: KINDS[r[3] as number] ?? 'other', area_ha: r[4] as number, country,
      ...(country === 'CAN' ? { province: reg } : { state: reg }), centroid: [r[7] as number, r[8] as number], bbox: [r[9], r[10], r[11], r[12]] as [number, number, number, number] } };
  });
}
export interface LandDetail {
  id: string; name: string; nation: string; kind: string; kind_label: string; jurisdiction: 'BC' | 'CA' | 'CAN' | 'US'; area_ha: number; area_acres: number;
  centroid: { lon: number; lat: number }; location_id: string; website: string | null; caveat: string;
  nearby: { id: string; name: string; kind: 'catalog farm' | 'prepared field'; lat: number; lon: number; crop?: string | null; acres?: number | null; distance_km: number }[];
  nearby_radius_km: number; source?: { title: string; url: string } | null;
}
const STATES: Record<string, string> = { AL: 'Alabama', AK: 'Alaska', AZ: 'Arizona', AR: 'Arkansas', CA: 'California', CO: 'Colorado', CT: 'Connecticut', DE: 'Delaware', DC: 'District of Columbia', FL: 'Florida', GA: 'Georgia', HI: 'Hawaii', ID: 'Idaho', IL: 'Illinois', IN: 'Indiana', IA: 'Iowa', KS: 'Kansas', KY: 'Kentucky', LA: 'Louisiana', ME: 'Maine', MD: 'Maryland', MA: 'Massachusetts', MI: 'Michigan', MN: 'Minnesota', MS: 'Mississippi', MO: 'Missouri', MT: 'Montana', NE: 'Nebraska', NV: 'Nevada', NH: 'New Hampshire', NJ: 'New Jersey', NM: 'New Mexico', NY: 'New York', NC: 'North Carolina', ND: 'North Dakota', OH: 'Ohio', OK: 'Oklahoma', OR: 'Oregon', PA: 'Pennsylvania', RI: 'Rhode Island', SC: 'South Carolina', SD: 'South Dakota', TN: 'Tennessee', TX: 'Texas', UT: 'Utah', VT: 'Vermont', VA: 'Virginia', WA: 'Washington', WV: 'West Virginia', WI: 'Wisconsin', WY: 'Wyoming', PR: 'Puerto Rico', GU: 'Guam', VI: 'U.S. Virgin Islands', AS: 'American Samoa', MP: 'Northern Mariana Islands',
  BC: 'British Columbia', AB: 'Alberta', SK: 'Saskatchewan', MB: 'Manitoba', ON: 'Ontario', QC: 'Quebec', NB: 'New Brunswick', NS: 'Nova Scotia', PE: 'Prince Edward Island', NL: 'Newfoundland and Labrador', YT: 'Yukon', NT: 'Northwest Territories', NU: 'Nunavut' };
/** State or province code of a land ("SK", "AZ"). */
export const regionOf = (p: LandProps) => (p.province ?? p.state ?? '') as string;
export const regionName = (r: string) => STATES[r] ?? r;
export const kindLabel = (k: string) => (k === 'reserve' ? 'Reserve' : k === 'other' ? 'Tribal area' : 'Tribal land');
const fmt = (n: number) => Math.round(n).toLocaleString('en-US');
/** "1,583 acres (641 ha)"; small lands show one decimal. */
export function areaText(ha: number) {
  const ac = ha * 2.47105;
  return `${ac < 100 ? ac.toFixed(1) : fmt(ac)} acres (${ha < 100 ? ha.toFixed(1) : fmt(ha)} ha)`;
}
export function boundsOf(f: LandFeature): [[number, number], [number, number]] {
  const bb = f.properties.bbox;
  if (bb) return [[bb[0], bb[1]], [bb[2], bb[3]]];
  if (f.geometry.type === 'Point') { const [x, y] = f.geometry.coordinates; return [[x - 0.01, y - 0.01], [x + 0.01, y + 0.01]]; }
  let w = 180, s = 90, e = -180, n = -90;
  const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
  for (const poly of polys) for (const [x, y] of poly[0]) { w = Math.min(w, x); e = Math.max(e, x); s = Math.min(s, y); n = Math.max(n, y); }
  return [[w, s], [e, n]];
}
