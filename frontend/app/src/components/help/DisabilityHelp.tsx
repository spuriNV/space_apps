// "Farming with a disability": real programs for the field's region, one plain line each and a link.
// Data: GET /api/help/disability (backend/api/data/disability_programs.json), filtered here by region.
import { useEffect, useState } from 'react';
import { API_BASE } from '../../api';
import './help.css';

interface Program { id: string; regions: string[]; name: string; who: string; line: string; url: string; verified: boolean; checked: string; note?: string }
let cache: Promise<Program[] | null> | null = null;
const load = () => (cache ??= fetch(`${API_BASE}/help/disability`).then((r) => (r.ok ? r.json() : null)).then((b) => (b?.programs as Program[]) ?? null).catch(() => null)).then((p) => { if (!p) cache = null; return p; });

export function DisabilityHelp({ region }: { region?: 'ca' | 'bc' | 'other' }) {
  const [all, setAll] = useState<Program[] | null | undefined>(undefined);
  useEffect(() => { let on = true; load().then((p) => on && setAll(p)); return () => { on = false; }; }, []);
  if (all === undefined) return null;
  const list = (all ?? []).filter((p) => !region || region === 'other' || p.regions.includes(region));
  if (!list.length) return null;
  return (
    <section className="dh" data-testid="disability-help" aria-labelledby="dh-h">
      <h2 className="fp-h" id="dh-h">Farming with a disability</h2>
      <p className="how">Free or funded help to keep farming after an injury, illness or disability.</p>
      <ul className="dh-list">
        {list.map((p) => (
          <li key={p.id}>
            <a href={p.url} target="_blank" rel="noreferrer"><b>{p.name}</b><span className="sr-only"> (opens in a new tab)</span></a>
            <span>{p.line}</span>
            {!p.verified && <small className="muted">Link not auto-checked; confirm on the program's own site.</small>}
          </li>
        ))}
      </ul>
    </section>
  );
}
