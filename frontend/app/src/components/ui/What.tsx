// Plain-language "What's this?" explanations, opened in place next to the word they explain.
import { useState } from 'react';

export const GLOSSARY = {
  et: { term: 'Crop water use (evapotranspiration, ET)', text: 'The water a crop pulls from the soil and gives off through its leaves, plus what evaporates from the ground. It is what irrigation and rain have to replace. Measured in inches, or acre-feet per acre (1 acre-foot per acre = 12 inches).' },
  greenness: { term: 'Greenness (NDVI)', text: 'How green the field looks from a satellite, on a 0 to 1 scale. Bare soil is below 0.2, a young or thin crop 0.2 to 0.35, and a full green canopy above 0.6. Standing water reads near 0.' },
  soilAnomaly: { term: 'Soil moisture against normal', text: 'Whether the top few feet of soil hold more or less water than usual for this time of year, ranked against the same dates in other years. 50 is a normal year; 90 means wetter than 9 years in 10. One reading covers several miles, not your field alone.' },
  frost: { term: 'Frost risk', text: 'Nights when the air near the ground drops to 32 °F or lower at the weather stations near the field. Low spots in a field can be a few degrees colder than the station.' },
  waterBalance: { term: 'Water balance (irrigation need)', text: 'Crop water use minus the rain that soaks in and stays in the root zone. What is left is the irrigation the crop needs, before losses in the ditch or the system.' },
  bare: { term: 'Bare days', text: 'Days the satellites see bare ground: greenness below 0.2 and no standing water. Bare soil in heavy rain loses topsoil; bare soil in heat dries out and crusts.' },
} as const;
export type GlossKey = keyof typeof GLOSSARY | 'opera' | 'stress' | 'ruleMl' | 'heat';
const EXTRA: Record<string, { term: string; text: string }> = {
  opera: { term: 'Standing water seen (NASA OPERA)', text: 'NASA’s OPERA product marks every 100 ft square that holds open or shallow water in each clear Landsat or Sentinel-2 image. It sees winter flooding that a greenness reading can miss.' },
  stress: { term: 'Crop-stress weeks', text: 'Growing-season weeks when the crop was greener than nothing but under strain: unusual heat, very thirsty air, or weaker growth than in its other years. Two statistical methods look for them; a week counts when either flags it.' },
  ruleMl: { term: 'Rule and machine learning', text: 'The rule calls a field bare below greenness 0.2 and flooded when the water index is high. The machine-learning version learns the same classes from neighbouring fields. We show both and say how often each was right in 2022, a year neither trained on.' },
  heat: { term: 'Hot days', text: 'Days when the weather stations near the field reach 104 °F or more. Above that, most crops close their leaves and stop growing, and bare soil bakes.' },
};
/** Texts from GET /api/glossary replace the built-in ones when the API serves real content. */
const API_KEY: Record<string, string> = { et: 'et', greenness: 'ndvi', soilAnomaly: 'soil_moisture_pct', frost: 'frost', waterBalance: 'water_balance', bare: 'cover_classes', opera: 'dswx', ruleMl: 'rule_vs_ml', heat: 'heat_days' };
let fromApi: Record<string, { term: string; short: string }> = {};
export const setGlossary = (g: Record<string, { term: string; short: string }>) => { fromApi = g; };

/** Small "What's this?" link that opens a plain explanation underneath. */
export function What({ k }: { k: GlossKey }) {
  const [open, setOpen] = useState(false);
  const a = fromApi[API_KEY[k] ?? k];
  const g = a ? { term: a.term, text: a.short } : (GLOSSARY as Record<string, { term: string; text: string }>)[k] ?? EXTRA[k];
  return (
    <span className="what">
      <button className="what-btn" onClick={() => setOpen(!open)} aria-expanded={open} title={g.term}>{open ? 'Close' : 'What’s this?'}</button>
      {open && <span className="what-text" role="note"><b>{g.term}.</b> {g.text}</span>}
    </span>
  );
}
