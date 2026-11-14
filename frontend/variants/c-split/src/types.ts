// Shapes follow planner-spec.md B3. Every numeric leaf is a SourcedNumber.
export interface Source { id: string; short?: string; title: string; url: string | null; accessed?: string; verified: boolean }
export interface SourcedNumber { value: number; unit: string; low: number | null; high: number | null; method: string; source: Source; note?: string }
export type Range = { value: number; low: number; high: number };

export interface FieldEvent { date: string; type: string; title: string; url: string | null; verified: boolean }
export interface Location {
  id: string; name: string; short_name: string; region_label: string; ground_data: string; current_crop: string;
  geometry: GeoJSON.Polygon; centroid: { lon: number; lat: number }; area_ha: SourcedNumber;
  soil: { muname: string; drainage_class: string; hydrologic_group: string; texture_class: string; source: Source };
  terrain: { note: string };
  water: { source: string; allocation_input: { unit: string; value: number }; district: string; sgma_subbasin: string; sgma_status: { text: string; url: string | null; verified: boolean } };
  market_preference: string;
  stations: { network: string; id: number | string; name: string; distance_km?: number }[];
  regional_cell: { grid: string; footprint: GeoJSON.Polygon };
  crop_history: Record<string, string>;
  observed_cover: { summary: string };
  events: FieldEvent[];
  headline: { bare_window: string; detector_agreement_pct: number; cells_30m: number };
  grid: { cols: number; rows: number; cell_m: number };
}
export interface BcCard { id: string; title: string; lines: string[]; next_step: string; centroid: { lon: number; lat: number } }

export type CoverState = 'w' | 'b' | 'p' | 'c' | 'u';
export type ScoreKey = 'water_use' | 'forage_value' | 'n_fixation' | 'erosion' | 'organic_matter' | 'market' | 'pest_break' | 'infiltration' | 'n_scavenging';
export type PriorityKey = 'water_use' | 'forage_value' | 'n_fixation' | 'erosion' | 'organic_matter' | 'market';
export type Weights = Record<PriorityKey, number>;

export interface BriefSentence { text: string; source_ids: string[]; numbers_used: string[]; author: 'llm' | 'template'; checked: boolean }
export interface RotationStrategy {
  id: string; location_id: string; name: string; short: string; is_baseline: boolean; cycle_years: number; year_shown: string | null; tagline: string;
  month_strip: { month: number; state: CoverState; label: string }[]; month_strip_source: string;
  exposure: {
    bare_days_per_year: SourcedNumber; exposed_rain_days: SourcedNumber; exposed_frost_days: SourcedNumber; exposed_heat_days: SourcedNumber;
    replay: Record<string, { exposed_rain_days: SourcedNumber; irrigation_need_mm: SourcedNumber }>; cover_basis: string;
  };
  water: { etc_mm_season: SourcedNumber; irrigation_need_mm: SourcedNumber; openet_et_mm_season: SourcedNumber | null; etc_vs_openet_pct: SourcedNumber | null };
  scores: Record<ScoreKey, SourcedNumber>;
  risk_profile: { rma_share_drought: SourcedNumber; rma_share_excess_moisture: SourcedNumber; rma_share_heat: SourcedNumber; rma_share_other: SourcedNumber; rma_years: number[]; rma_label: string };
  funding: { program: string; rate_per_acre_usd: { value: number | null; note?: string }; url: string; verified: boolean }[];
  brief: {
    why: BriefSentence[]; evidence: BriefSentence[]; gaps: string[]; local_review: { item: string; severity: 'high' | 'medium' | 'low' }[];
    llm_report: { sentences: number; numbers_checked: number; rejected: number; model: string; cached_at: string };
  };
  uncertainty: { agronomic_gap_count: number; detector_disagreement_pct: number };
}
/** Result of POST /api/locations/{id}/score */
export interface ScoredStrategy extends RotationStrategy { composite: Range & { weights_used: Weights }; rank: number; tie: boolean; best: boolean }

export interface YearRow { year: number; cdl_crop: string; weeks: { rule: string; ml: string }; greenup_week: number | null; senescence_week: number | null; risks: { week: number; type: 'rain' | 'frost' | 'heat' }[] }
export interface FieldYear {
  location_id: string; years: YearRow[]; detector_agreement_pct: number;
  models: { id: string; method: string; labels: string; metrics: { accuracy: number; f1_bare: number; transition_mae_days: number }; notes: string }[];
}
export interface NewsItem { date: string; title: string; source: string; url: string | null; rank: number; kind: 'drought' | 'flood' | 'policy'; label: string; signal: { dataset: string; text: string; value_pct: number; lead_days: number | null } | null; verified: boolean }
export interface CellProps { id: number; row: number; col: number; ndvi: number; et_mm_day: number; lst_anom_k: number; cover_class: string; stress_hotspot: boolean }
export interface CellGrid extends GeoJSON.FeatureCollection<GeoJSON.Polygon, CellProps> { scene_date: string; scene_source: Source; et_source: Source }
