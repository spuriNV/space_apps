import { useState } from 'react';
import { IS_MOCK, PRIORITIES, getLocations } from '../api';
import type { PriorityKey, Weights } from '../types';
import { Icon } from './Bits';

const ICONS: Record<PriorityKey, string> = { water_use: 'drop', forage_value: 'cow', n_fixation: 'leaf', erosion: 'rain', organic_matter: 'soil', market: 'market' };

export default function TopBar({ weights, onToggle, onOpen, onHome, fieldName }: { weights: Weights; onToggle: (k: PriorityKey) => void; onOpen: (id: string) => void; onHome: () => void; fieldName: string | null }) {
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(false);
  const locs = getLocations().filter((l) => (l.name + l.region_label).toLowerCase().includes(q.toLowerCase()));
  return (
    <header className="topbar">
      <button className="brand" onClick={onHome} aria-label="Field Shift home">
        <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden><rect width="32" height="32" rx="8" fill="#188038" /><path d="M6 22c5-1 7-5 10-5s5 4 10 5M6 16c5-1 7-5 10-5s5 4 10 5" stroke="#fff" strokeWidth="2.4" fill="none" strokeLinecap="round" /></svg>
        <span>Field Shift</span>
      </button>
      <div className="search" data-open={open}>
        <Icon name="search" size={18} />
        <input
          placeholder={fieldName ?? 'Search California fields'} value={q} aria-label="Search fields"
          onChange={(e) => setQ(e.target.value)} onFocus={() => setOpen(true)} onBlur={() => setTimeout(() => setOpen(false), 150)}
        />
        {open && (
          <div className="search-menu">
            <div className="search-head">Example fields</div>
            {locs.map((l) => (
              <button key={l.id} onMouseDown={() => { onOpen(l.id); setQ(''); }}>
                <Icon name="pin" /><span><b>{l.short_name}</b><small>{l.region_label}</small></span>
              </button>
            ))}
            {locs.length === 0 && <div className="search-empty">No example field matches. California only for now.</div>}
            <div className="search-foot"><Icon name="info" size={14} />Draw-your-own field: California only, coming with the live backend</div>
          </div>
        )}
      </div>
      <div className="pills" role="group" aria-label="What matters most">
        <span className="pills-label">What matters most</span>
        {PRIORITIES.map((p) => (
          <button key={p.key} className="pill" aria-pressed={weights[p.key] > 1} title={p.hint} onClick={() => onToggle(p.key)} data-priority={p.key}>
            <Icon name={ICONS[p.key]} size={15} />{p.label}
          </button>
        ))}
      </div>
      <div className="top-right">
        {IS_MOCK && <span className="mockbadge" title="Numbers on this prototype are illustrative. Dates, events and links are real and cited."><i />Mock data</span>}
      </div>
    </header>
  );
}
