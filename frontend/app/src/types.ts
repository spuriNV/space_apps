// Shapes follow planner-spec.md B3. Only the fields this prototype reads are typed strictly.
export interface Source { id: string; title?: string; url: string | null; accessed?: string; verified: boolean }
export interface SourcedNumber { value: number; low: number | null; high: number | null; unit: string; method: string; source?: Source; note?: string; blocked?: boolean }

export interface FieldEvent { date: string; end_date?: string; type: 'drought_fallow' | 'atmospheric_river' | 'sgma_probation'; short: string; title: string; detail?: string; url: string | null; verified: boolean }

export interface Location {
  id: string; name: string; short_name: string; valley: string; ground_data: string; headline: string;
  geometry: { type: 'Polygon'; coordinates: number[][][] };
  centroid: { lon: number; lat: number };
  area_ha: SourcedNumber;
  soil: { muname: string; drainage_class: string; hydrologic_group: string; texture_class: string; awc_mm_per_m: SourcedNumber; om_pct?: SourcedNumber; ec_ds_per_m?: number; texture_detail?: { sand_pct: number; silt_pct: number; clay_pct: number } };
  county?: string; dwr_id?: string; boundary_title?: string; cdl_source?: Source;
  terrain: { slope_mean_pct: SourcedNumber; note: string };
  water: { source: string; allocation_input: { unit: string; value: number }; district: string; sgma_subbasin: string; sgma_status: { text: string; url: string; verified: boolean } };
  market_preference: string;
  stations: { network: string; id: number | string; name: string; distance_km?: number }[];
  crop_history: Record<string, string>;
  observed_cover: { summary: string };
  events: FieldEvent[];
}

export type CoverClass = 'b' | 'p' | 'c' | 'w' | 'u';
export interface CalendarYear { year: number; cdl: string; rule: string; ml: string; ndvi: number[]; et_mm_day: number[]; greenup_dekad: number | null; senescence_dekad: number | null; risks: { dekad: number; type: 'rain' | 'frost' | 'heat' | 'dry'; label: string }[] }
export interface Calendar { location_id: string; detector_agreement_pct: SourcedNumber; years: CalendarYear[]; real?: boolean }

export interface Series { dataset: string; label: string; native_scale?: string; unit: string; values: (number | null)[]; years?: number[]; gap_note?: string }
export interface Regional { smap_rootzone_pct: Series; grace_gw_pct: Series; imerg_mm_dekad: Series; dwr_well_depth_m: Series; heatwave_days: Series; modis_ndvi_anom: Series }

export interface CellProps { id: number; r: number; c: number; v: number; low: number; edge: boolean; nd?: Record<string, number | null> }
export interface GridLayer { key: string; kind: 'quarter_median' | 'scene'; year?: number; quarter?: number; n_scenes?: number; date?: string; target?: string; scene_id?: string }
export interface CellGrid { cell_m: number; rows: number; cols: number; layers?: GridLayer[]; type: 'FeatureCollection'; features: { type: 'Feature'; properties: CellProps; geometry: { type: 'Polygon'; coordinates: number[][][] } }[] }

export type ScoreKey = 'water_use' | 'forage_value' | 'n_fixation' | 'erosion' | 'organic_matter' | 'market' | 'pest_break' | 'infiltration' | 'n_scavenging';
export interface RotationStrategy {
  id: string; location_id: string; name: string; short_name: string; is_baseline: boolean; cycle_years: number;
  calendar_months: string[]; month_cover: string; strip_year?: number; allocation_rule: string | null;
  exposure: { bare_days_per_year: SourcedNumber; exposed_rain_days: SourcedNumber; exposed_heat_days: SourcedNumber; cover_basis: string; replay: Record<string, { irrigation_need_mm: SourcedNumber; exposed_rain_days: SourcedNumber; note: string }> };
  water: { etc_mm_season: SourcedNumber; irrigation_need_mm: SourcedNumber; etc_by_month_mm: number[]; openet_et_mm_season: SourcedNumber | null; etc_vs_openet_pct: SourcedNumber | null };
  scores: Record<ScoreKey, SourcedNumber>;
  composite: SourcedNumber;
  risk_profile: { rma_share_drought: SourcedNumber; rma_share_excess_moisture: SourcedNumber; rma_share_heat: SourcedNumber; rma_years: number[]; crop: string; note: string; blocked?: boolean };
  funding: { program: string; url: string; verified: boolean; rate_per_acre_usd?: SourcedNumber }[];
  constraints_check?: { constraint: string; status: string; detail: string; source?: Source }[];
  brief: { why: { text: string; author: string; checked: boolean }[]; evidence?: { text: string }[]; gaps?: { text: string }[] | string[]; local_review: { item: string; severity: string }[]; llm_report?: { sentences: number; numbers_checked: number; rejected: number } | null };
  uncertainty: { agronomic_gap_count: number };
}

export interface NewsItem { date: string; title: string; source: string; url: string | null; rank: number; verified: boolean; date_note?: string; signal: { dataset: string; label: string; value_pct: number | null; lead_days: number | null } }
export interface Dataset { id: string; name: string; long_name: string; sees: string; native_scale: string; footprint_m: number; cadence: string; since: number; group: 'field' | 'regional'; color: string; in_stack?: string; caveat?: string }
export interface BCInfo { title: string; intro: string; lines: { label: string; text: string }[]; limit: string; places: { name: string; lat: number; lon: number }[]; news: { date: string; title: string; source: string; url: string; verified: boolean }[]; next_step: { label: string; ref: string } }
export interface StoryChapter { date: string; camera: 'card' | 'drill'; title: string; saw: { dataset: string; scale: string; series: 'smap' | 'grace' | 'imerg' | 'cover'; text: string }; reported: string[] }
export interface Story { title: string; window: [number, number]; chapters: StoryChapter[] }
