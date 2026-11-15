// Sources behind the field view — BC Salmon River demo (same groups as the CA build, BC datasets).
import Icon from '../Icons';

const GROUPS: { title: string; items: [string, string][] }[] = [
  { title: 'NASA', items: [
    ['HLS (Harmonized Landsat Sentinel-2), NASA/USGS', 'Bare, green or flooded every few days; the field calendar. 30 m.'],
    ['Landsat 8 and 9, NASA/USGS', 'Greenness since 2016, inside HLS and the 3D view. 30 m.'],
    ['GPM IMERG, NASA/JAXA', 'Daily rain over the field; rain since 1 Oct and its 2001–2025 normal. 0.1°.'],
    ['GRACE-FO data assimilation, NASA', 'Groundwater and root-zone soil moisture percentiles, weekly. 0.25°.'],
    ['OPERA surface water (DSWx), NASA JPL', 'Standing water on the field in each clear image. 30 m.'],
    ['NASA POWER', 'Sun, wind and humidity for crop water use (the rotation model). Real at this field. 0.5°.'],
    ['NASADEM, NASA JPL', 'Slope and low spots. 30 m.'],
    ['Astronaut photography, NASA Johnson Space Center', 'ISS photo of the region when available.'],
  ] },
  { title: 'Other satellites', items: [
    ['Sentinel-2, ESA (Copernicus)', '100 ft squares in the 3D view; also inside HLS. 10–20 m.'],
  ] },
  { title: 'Ground data', items: [
    ['AAFC Annual Crop Inventory', 'Crop grown each year at this point (pasture/forages for this demo), from 2011 on.'],
    ['BC soil / SoilGrids', 'Soil type and water held for this illustrative outline.'],
    ['Environment Canada / Salmon Arm CS', 'Nearest daily weather station; the engine uses NASA POWER at the field.'],
    ['BC Water Sustainability Act / fish-protection orders', 'Licence story and the August 2023 forage irrigation stop on the Salmon River.'],
    ['NOAA Climate Prediction Center', 'Winter rain and temperature outlooks at this location.'],
  ] },
  { title: 'Models', items: [
    ['CropLytics rotation model', 'FAO-56 crop water use and rules of thumb for soil, feed and pests; NASA POWER weather at this point.'],
    ['Bare / green / flooded rule', 'Greenness below 0.2 is bare, 0.2–0.35 thin; water index for flooding.'],
    ['Machine-learning calendar (random forest)', 'Second opinion on the cover rule; treat agreement as illustrative on this BC field.'],
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
