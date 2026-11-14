// "Sources": every dataset and model behind the field view, grouped like the brief's sources section. One line each.
import Icon from '../Icons';

const GROUPS: { title: string; items: [string, string][] }[] = [
  { title: 'NASA', items: [
    ['HLS (Harmonized Landsat Sentinel-2), NASA/USGS', 'Bare, green or flooded every few days; the field calendar. 30 m.'],
    ['Landsat 8 and 9, NASA/USGS', 'Greenness since 2016, inside HLS and the 3D view. 30 m.'],
    ['GPM IMERG, NASA/JAXA', 'Daily rain over the field; rain since 1 Oct and its 2001–2025 normal. 0.1°.'],
    ['GRACE-FO data assimilation, NASA', 'Groundwater and root-zone soil moisture percentiles, weekly. 0.25°.'],
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
    ['USDA soil survey (SSURGO)', 'Soil type, water held, drainage, salt.'],
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

export function SourcesSheet({ onClose }: { onClose: () => void }) {
  return (
    <div className="src-wrap" role="dialog" aria-label="Sources" onClick={onClose} data-testid="sources">
      <div className="src-sheet" onClick={(e) => e.stopPropagation()}>
        <header><h2>Sources</h2><button className="sq-btn" onClick={onClose} title="Close"><Icon name="close" size={16} /></button></header>
        <div className="src-cols">
          {GROUPS.map((g) => (
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
