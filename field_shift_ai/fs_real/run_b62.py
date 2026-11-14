import json, pandas as pd
from fieldshift_models.stress import run_stress
w = pd.read_csv('data/weekly_ca.csv')
res = run_stress(w, 'out', seed=0)
s = res.summaries['ca_colusa_rice']
avail = {c: int(res.weekly[c].notna().sum()) for c in ['z_ndvi','z_lst','z_esi','z_sm','z_eto','z_imerg30']}
print('weeks scored:', len(res.weekly), '| non-missing per feature:', avail)
print('flag rate  zscore=%.3f  iforest=%.3f  agreement=%.3f' % (s['evaluation']['flag_rate_zscore'], s['evaluation']['flag_rate_iforest'], s['evaluation']['agreement']))
for e in s['evaluation']['events']: print('event:', e)
print('false-positive proxy (wet & cool weeks):', s['evaluation']['wet_cool_weeks'], 'weeks; zscore', s['evaluation']['false_positive_proxy_zscore'], 'iforest', s['evaluation']['false_positive_proxy_iforest'])
print('check #8:', s['checks'])
print('evidence:', s['evidence'])
g = res.weekly.groupby('year')[['flag_zscore','flag_iforest']].sum().astype(int).T; print(g)
