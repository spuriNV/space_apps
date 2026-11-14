// The only place the UI reads data from.
// Today: src/mock/*.json (illustrative, shaped like planner-spec.md B3).
// Later: swap each function body for fetch(`${API}/...`) against backend/api (routes noted per function).
import locationsJson from './mock/locations.json';
import strategiesJson from './mock/strategies.json';
import zonesJson from './mock/zones.json';
import yearJson from './mock/year.json';
import trendsJson from './mock/trends.json';
import newsJson from './mock/news.json';
import modelsJson from './mock/models.json';
import bcJson from './mock/bc.json';
import sourcesJson from './mock/sources.json';
import type { BcCard, FieldYear, Location, LocationId, ModelReport, NewsItem, RotationStrategy, Source, Trends, Zones } from './types';

export const API = 'http://localhost:8000/api';
export const IS_MOCK = true;

const cast = <T,>(v: unknown) => v as T;

/** GET /api/locations */
export const getLocations = (): Location[] => cast<Location[]>(locationsJson);
/** GET /api/locations/{id} */
export const getLocation = (id: LocationId): Location => getLocations().find((l) => l.id === id)!;
/** GET /api/locations/{id}/strategies (POST .../score once weights and scenario are live) */
export const getStrategies = (id: LocationId): RotationStrategy[] => cast<Record<string, RotationStrategy[]>>(strategiesJson)[id];
/** GET /api/locations/{id}/zones */
export const getZones = (id: LocationId): Zones => cast<Record<string, Zones>>(zonesJson)[id];
/** GET /api/locations/{id}/features/weekly */
export const getFieldYear = (id: LocationId): FieldYear => cast<Record<string, FieldYear>>(yearJson)[id];
/** GET /api/locations/{id}/trends?layer= */
export const getTrends = (id: LocationId): Trends => cast<Record<string, Trends>>(trendsJson)[id];
/** GET /api/locations/{id}/news */
export const getNews = (id: LocationId): NewsItem[] => cast<Record<string, NewsItem[]>>(newsJson)[id];
/** GET /api/locations/{id}/models */
export const getModels = (id: LocationId): ModelReport[] => cast<Record<string, ModelReport[]>>(modelsJson)[id];
/** GET /api/bc/news + static card copy */
export const getBcCard = (): BcCard => cast<BcCard>(bcJson);
export const getSources = (): Record<string, Source> => cast<Record<string, Source>>(sourcesJson);
