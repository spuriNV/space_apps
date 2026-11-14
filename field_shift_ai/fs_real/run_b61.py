import pandas as pd
from fieldshift_models.bare_cover import run_bare_cover
obs = pd.read_csv('data/obs_ca.csv')
for sp in ['year','ca_fallow']:
    res = run_bare_cover(obs, sp, 'out', seed=0)
    print(f'== split {sp}:', res.reports[0]['split'], '| dropped (no data):', res.reports[1]['features_dropped_no_data'])
    for r in res.reports:
        m = r['metrics']
        print(f"  {r['method']:<14} train_acc={m.get('train_accuracy','-')!s:.5} test_acc={m['accuracy']:.3f} f1_bare={m['f1_bare']:.3f} n_test_lab={m['n_labelled']} "
              f"trans_mae_d={m['transition_mae_days']!s:.5} ({m['transitions_matched']}/{m['transitions_reference']}) vs_rule={r['disagreement_with'].get('rule_ndvi','-')!s:.5} badge={r.get('badge')}")
        print('     confusion rows=true [bare,partial,covered]:', r['confusion'])
        if r['feature_importance']:
            print('     top features:', [(f['feature'], round(f['share'],2)) for f in r['feature_importance'][:5]])
