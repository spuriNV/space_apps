// Single data-access seam (CONTRACT.md). Today: mock JSON in src/mock.
// Later: swap each body for fetch(`${API}/api/...`) using the spec B3 routes noted beside each call.
import type { Story, BCInfo, Calendar, CellGrid, Dataset, Location, NewsItem, Regional, RotationStrategy } from './types';
import locations from './mock/locations.json';
import cells from './mock/cells.json';
import calendar from './mock/calendar.json';
import regional from './mock/regional.json';
import strategies from './mock/strategies.json';
import news from './mock/news.json';
import datasets from './mock/datasets.json';
import bc from './mock/bc.json';
import story from './mock/story.json';

export const IS_MOCK = true;
export const API = 'http://localhost:8000';
const ok = <T,>(v: unknown) => Promise.resolve(v as T);
type ById<T> = Record<string, T>;

/** GET /api/locations */
export const getLocations = () => ok<Location[]>(locations);
/** GET /api/locations/{id}/zones (30 m cell grid) */
export const getCells = (id: string) => ok<CellGrid>((cells as unknown as ById<CellGrid>)[id]);
/** GET /api/locations/{id}/features/weekly (cover classes by detector, NDVI, ET, risk days) */
export const getCalendar = (id: string) => ok<Calendar>((calendar as unknown as ById<Calendar>)[id]);
/** GET /api/locations/{id}/trends?layer=... */
export const getRegional = (id: string) => ok<Regional>((regional as unknown as ById<Regional>)[id]);
/** GET /api/locations/{id}/strategies (POST .../score once weights are live) */
export const getStrategies = (id: string) => ok<RotationStrategy[]>((strategies as unknown as RotationStrategy[]).filter((s) => s.location_id === id));
/** GET /api/locations/{id}/news */
export const getNews = (id: string) => ok<NewsItem[]>((news as unknown as ById<NewsItem[]>)[id]);
/** dataset catalogue for the layers drawer (static; mirrors Location.datasets) */
export const getDatasets = () => ok<Dataset[]>(datasets);
/** GET /api/bc/news + static card text */
export const getBC = () => ok<BCInfo>(bc);
/** story mode chapters (static editorial content; news joined from /api/locations/{id}/news) */
export const getStory = (id: string) => ok<Story>((story as unknown as ById<Story>)[id]);
