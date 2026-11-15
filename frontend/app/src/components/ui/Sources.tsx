// "Sources": every dataset and model behind the field view, grouped like the brief's sources section. One line each.
import Icon from '../Icons';

const GROUPS: { title: string; items: [string, string][] }[] = [
  { title: 'NASA', items: [
    ['HLS (Harmonized Landsat Sentinel-2), NASA/USGS', 'Bare, green or flooded every few days; the field calendar. 30 m.'],
    ['Landsat 8 and 9, NASA/USGS', 'Greenness since 2016, inside HLS and the 3D view. 30 m.'],
    ['GPM IMERG, NASA/JAXA', 'Daily rain over the field; rain since 1 Oct and its 2001–2025 normal. 0.1°.'],
    ['GRACE-FO data assimilation, NASA', 'Groundwater and root-zone soil moisture percentiles, weekly, run through a land model. One reading for a 17-mile square; the satellites themselves sense about 190 miles. Groundwater is the whole basin, not your own well.'],
    ['SMAP, NASA', 'Root-zone soil moisture, one reading for a 6-mile square, when its readings are in.'],
    ['OPERA surface water (DSWx), NASA JPL', 'Standing water on the field in each clear image. 30 m.'],
    ['NASA POWER', 'Sun, wind and humidity for crop water use (the rotation model). 0.5°.'],
    ['NASADEM, NASA JPL', 'Slope and low spots. 30 m.'],
    ['Astronaut photography, NASA Johnson Space Center', 'The ISS photo of the valley. Image courtesy of the Earth Science and Remote Sensing Unit, NASA Johnson Space Center.'],
  ] },
  { title: 'Other satellites', items: [
    ['Sentinel-2, ESA (Copernicus)', '100 ft squares in the 3D view; also inside HLS. 10–20 m.'],
    ['OpenET ensemble', 'Measured crop water use on this field, monthly, 2016–2025; the check on our model.'],
  ] },
  { title: 'Ground data', items: [
    ['NOAA weather stations (GHCN-Daily)', 'Hot days (104 °F), frost nights, heavy-rain days.'],
    ['USDA Cropland Data Layer', 'The crop grown each year, 2008–2025.'],
    ['USDA soil survey (SSURGO)', 'Soil type, sand, silt and clay (top 3 feet), water held, drainage, salt.'],
    ['DWR / Land IQ crop mapping 2023', 'The field outline and state field number.'],
    ['USDA Risk Management Agency', 'Crop-insurance payouts by county, crop and cause.'],
    ['NOAA Climate Prediction Center, US Drought Monitor', 'Winter outlooks and drought, county.'],
    ['California Data Exchange Center (CDEC), Reclamation, DWR', 'Reservoir storage, allocations, snowpack.'],
  ] },
  { title: 'Models', items: [
    ['CropLytics rotation model', 'FAO-56 crop water use and the rules of thumb for soil, feed and pests; weather 2015–2025.'],
    ['Bare / green / flooded rule', 'Greenness below 0.2 is bare, 0.2–0.35 thin; water index for flooding.'],
    ['Machine-learning calendar (random forest)', 'A second opinion on the rule, trained on neighbouring fields; tested on 2022.'],
    ['Crop-stress weeks', 'Two statistical methods on greenness, heat and dry air, growing season only.'],
  ] },
];

/** A BC field: its own ground data, in place of the California-only sources (the NASA and model groups are the same). */
const BC_GROUND: { title: string; items: [string, string][] } = { title: 'Ground data (British Columbia)', items: [
  ['Environment and Climate Change Canada (ECCC) daily climate', 'Hot days, frost nights and station rain: Salmon Arm CS, and Silver Creek until 2021.'],
  ['AAFC Annual Crop Inventory', 'The crop grown each year, 2011–2025. One class for hay and pasture; no alfalfa class.'],
  ['ParcelMap BC and the Agricultural Land Reserve', 'The field outline: a farmland parcel clipped to forage pixels. No owner or parcel number kept.'],
  ['AAFC Soil Landscapes of Canada v3.2', 'Soil texture, water held and drainage from a 1:1,000,000 map; not field scale.'],
  ['BC Gov News, Water Sustainability Act orders', 'The 2023 and 2026 orders to stop irrigating in the Salmon River watershed.'],
  ['Indian reserves (CLSS boundaries), BC Data Catalogue', 'Reserve outlines and distances, for context only; no reserve land was analysed.'],
] };
const CA_ONLY = /NOAA weather|Cropland Data|SSURGO|DWR \/ Land IQ|Risk Management|Climate Prediction|CDEC/;

export function SourcesSheet({ onClose, bc = false }: { onClose: () => void; bc?: boolean }) {
  const groups = bc ? [...GROUPS.filter((g) => g.title !== 'Ground data'), BC_GROUND].map((g) => ({ ...g, items: g.items.filter(([n]) => !CA_ONLY.test(n) && !/OpenET/.test(n)) })) : GROUPS;
  return (
    <div className="src-wrap" role="dialog" aria-label="Sources" onClick={onClose} data-testid="sources">
      <div className="src-sheet" onClick={(e) => e.stopPropagation()}>
        <header><h2>Sources</h2><button className="sq-btn" onClick={onClose} title="Close"><Icon name="close" size={16} /></button></header>
        <div className="src-cols">
          {groups.map((g) => (
            <section key={g.title}>
              <h3>{g.title}</h3>
              <ul>{g.items.map(([n, d]) => <li key={n}><b>{n}</b><span>{d}</span></li>)}</ul>
            </section>
          ))}
        </div>
        <p className="src-foot">Every number in CropLytics comes from one of these, or is marked as our assumption. It supports the grower and adviser; it does not replace either.</p>
      </div>
    </div>
  );
}
