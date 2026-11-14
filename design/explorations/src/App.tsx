import { useState } from 'react';
import { cropOf } from './data';
import { BottomBar, Rail, Satellite, Switcher, YearStrip } from './shell';
import Year1 from './year/Year1';
import Year2 from './year/Year2';
import Year3 from './year/Year3';
import Compare1 from './compare/Compare1';
import Compare2 from './compare/Compare2';
import Compare3 from './compare/Compare3';
import { Weather, WEATHER_LABEL } from './compare/common';

const q = new URLSearchParams(location.search);
const screen = (q.get('screen') === 'compare' ? 'compare' : 'year') as 'year' | 'compare';
const opt = Math.min(3, Math.max(1, +(q.get('opt') ?? 1) || 1));
const STORY = [2024, 2022, 2023];

export default function App() {
  const [year, setYear] = useState(+(q.get('year') ?? (opt === 1 ? 2023 : 2022)));
  const [weather, setWeather] = useState<Weather>((q.get('weather') as Weather) ?? 'typical');
  const pickYear = (y: number) => (opt === 3 ? STORY.includes(y) && setYear(y) : setYear(y));

  return (
    <div className="app">
      <Satellite cx={screen === 'year' && opt === 1 ? 1195 : 720} cy={screen === 'year' && opt === 1 ? 440 : 450} label={screen === 'year' && opt === 1} />
      <Rail on={screen === 'year' ? 'Year' : 'Compare'} />
      <Switcher screen={screen} opt={opt} />
      {screen === 'year' && opt === 1 && <Year1 year={year} />}
      {screen === 'year' && opt === 2 && <Year2 year={year} setYear={setYear} />}
      {screen === 'year' && opt === 3 && <Year3 year={year} setYear={setYear} />}
      {screen === 'compare' && opt === 1 && <Compare1 weather={weather} />}
      {screen === 'compare' && opt === 2 && <Compare2 weather={weather} pickId={q.get('alt') ?? undefined} />}
      {screen === 'compare' && opt === 3 && <Compare3 weather={weather} initA={q.get('a') ?? undefined} initB={q.get('b') ?? undefined} />}

      {screen === 'year' ? (
        <BottomBar title={`${year} · ${cropOf(year)}`} sub={opt === 3 ? 'Story years highlighted' : 'Pick a year · 2016–2025'}>
          <YearStrip selected={opt === 3 ? [year] : [year]} onPick={pickYear} />
        </BottomBar>
      ) : (
        <BottomBar title="Test against" sub={WEATHER_LABEL[weather]}>
          <div className="wx">
            {(['typical', '2022', '2023'] as Weather[]).map((w) => (
              <button key={w} className={w === weather ? 'on' : ''} onClick={() => setWeather(w)}>
                {w === 'typical' ? 'Typical year' : w === '2022' ? '2022 drought' : '2023 storms'}
              </button>
            ))}
          </div>
          <YearStrip selected={weather === 'typical' ? [] : [+weather]} onPick={(y) => (y === 2022 || y === 2023) && setWeather(String(y) as Weather)} />
        </BottomBar>
      )}
    </div>
  );
}
