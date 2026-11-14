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
export type GlossKey = keyof typeof GLOSSARY;

/** Small "What's this?" link that opens a plain explanation underneath. */
export function What({ k }: { k: GlossKey }) {
  const [open, setOpen] = useState(false);
  const g = GLOSSARY[k];
  return (
    <span className="what">
      <button className="what-btn" onClick={() => setOpen(!open)} aria-expanded={open} title={g.term}>{open ? 'Close' : 'What’s this?'}</button>
      {open && <span className="what-text" role="note"><b>{g.term}.</b> {g.text}</span>}
    </span>
  );
}
