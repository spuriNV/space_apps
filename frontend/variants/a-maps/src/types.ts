// Types mirror planner-spec.md B3. Kept loose where the spec uses {…}.
export interface Source { id: string; title: string; url: string | null; verified: boolean }
export interface SourcedNumber { value: number; unit: string; low: number | null; high: number | null; method: string; source: Source; note?: string }
export type Geometry = { type: 'Polygon'; coordinates: number[][][] };
export type LocationId = 'car_colusa_rice' | 'caf_tulare_forage';

export interface FieldEvent { date: string; type: string; title: string; url: string | null; verified: boolean }
export interface Station { network: string; id: number | string | null; name: string; distance_km?: number; url?: string }
export interface Location {
  id: LocationId; name: string; short_name: string; place_line: string; ground_data: string; regime: string;
  geometry: Geometry; centroid: { lon: number; lat: number }; area_ha: SourcedNumber;
  soil: { muname: string; drainage_class: string; hydrologic_group: string; awc_mm_per_m: SourcedNumber; om_pct: SourcedNumber; texture_class: string; source: Source };
  terrain: { slope_mean_pct: SourcedNumber; elev_m: SourcedNumber; note: string };
  water: { source: string; allocation_input: { unit: string; value: number }; district: string; sgma_subbasin: string; sgma_status: { text: string; url: string; verified: boolean }; cdec_stations: string[] };
  market_preference: string; stations: Station[];
  regional_cell: { grid: string; footprint: Geometry };
  datasets: string[]; crop_history: Record<string, string>;
  observed_cover: { summary: string; detector: string };
  baseline_summary: string; events: FieldEvent[];
}

export type ScoreKey = 'water_use' | 'forage_value' | 'n_fixation' | 'erosion' | 'organic_matter' | 'market' | 'pest_break' | 'infiltration' | 'n_scavenging';
export interface ReplayYear { exposed_rain_days: SourcedNumber; irrigation_need_mm: SourcedNumber; note: string }
export interface RotationStrategy {
  id: string; location_id: LocationId; name: string; short: string; is_baseline: boolean; cycle_years: number; one_line: string;
  month_labels: string[]; month_cover: string; shown_year: string | null; allocation_rule: string | null;
  exposure: { cover_basis: string; bare_days_per_year: SourcedNumber; exposed_rain_days: SourcedNumber; exposed_heat_days: SourcedNumber; exposed_frost_days: SourcedNumber; replay: Record<string, ReplayYear> };
  water: { etc_mm_season: SourcedNumber; irrigation_need_mm: SourcedNumber; openet_et_mm_season: SourcedNumber | null; etc_vs_openet_pct: SourcedNumber | null };
  scores: Record<ScoreKey, SourcedNumber>; income: SourcedNumber;
  composite: { value: number; low: number; high: number };
  risk_profile: { rma_share_drought: SourcedNumber; rma_share_excess_moisture: SourcedNumber; rma_share_heat: SourcedNumber; rma_share_other: SourcedNumber; rma_years: number[]; crop: string };
  funding: { program: string; url: string; verified: boolean }[];
  brief: { why: { text: string; author: string; checked: boolean }[]; local_review: { item: string; severity: string }[] };
  uncertainty: { agronomic_gap_count: number; detector_disagreement_pct: number };
}

export interface YearRow {
  year: number; cdl_class: string | null; rule: string; ml: string; ndvi: number[]; rain_mm: number[];
  risk_weeks: { extreme_rain: number[]; frost: number[]; heat: number[] };
  stress_weeks: { week: number; flagged_by: string }[]; bare_days: number;
}
export interface FieldYear { location_id: LocationId; detector_agreement_pct: SourcedNumber; risk_rules: Record<string, string>; years: YearRow[] }

export type MeasureKey = 'ndvi' | 'et_mm' | 'stress' | 'bare_days';
export interface Zones {
  location_id: LocationId; cell_size_m: number;
  measures: Record<MeasureKey, { label: string; unit: string; dataset: string; source: Source }>;
  hotspot_note: string; slope_note: string;
  footprints: { smap_9km: { label: string; size_m: number; geometry: Geometry }; modis_250m: { label: string; size_m: number; geometry: Geometry }; hls_30m: { label: string; size_m: number } };
  cells: GeoJSON.FeatureCollection<GeoJSON.Polygon, { i: number; j: number; ndvi: number; et_mm: number; stress: number; hotspot: boolean; bare_days: number; v: number }>;
}
export type TrendLayer = 'smap_anomaly' | 'grace_gw_pct';
export interface Trends {
  location_id: LocationId;
  layers: Record<TrendLayer, { label: string; unit: string; year: number; source: Source; domain: number[]; note?: string }>;
  cells: GeoJSON.FeatureCollection<GeoJSON.Polygon>;
  series: Record<string, { year: number; value: number }[]>;
  event_markers: { year: number; label: string }[];
}
export interface NewsItem { date: string; title: string; source: string; url: string | null; rank: number; place_match: string[]; verified: boolean; signal: { dataset: string; label: string; value_pct: number; lead_days: number | null } | null }
export interface ModelReport { id: string; task: string; method: string; split: { train_years: number[]; test_years: number[] }; metrics: { accuracy: number; f1_bare: number; transition_mae_days: number }; notes: string }
export interface BcCard {
  id: string; name: string; place_line: string; centroid: { lon: number; lat: number }; summary: string;
  reasons: { title: string; text: string }[]; limits_line: string; next_step: { label: string; items: string[] }; news: NewsItem[];
}
