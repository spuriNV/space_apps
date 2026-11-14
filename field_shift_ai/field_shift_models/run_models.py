#!/usr/bin/env python3
"""Train/evaluate the B6.1 and B6.2 models and write cached outputs.

  python run_models.py bare   --obs data/hls_obs.csv --out cache/models [--split year|ca_fallow|cross_site]
  python run_models.py stress --weekly data/weekly.csv --out cache/models [--loyo]
  python run_models.py demo   --out /tmp/fs_demo      # FAKE synthetic data, smoke test only
"""
import argparse
import json

import pandas as pd

from fieldshift_models.bare_cover import SPLITS, run_bare_cover
from fieldshift_models.stress import run_stress


def _read(path):
    return pd.read_parquet(path) if str(path).endswith(".parquet") else pd.read_csv(path)


def _print_bare(res):
    for r in res.reports:
        m = r["metrics"]
        print(f"  {r['location_id']:<22} {r['method']:<14} acc={m['accuracy']!s:.6} "
              f"f1_bare={m['f1_bare']!s:.6} trans_mae_d={m['transition_mae_days']!s:.5} "
              f"vs_rule={r['disagreement_with'].get('rule_ndvi', '-')!s:.5} badge={r.get('badge')}")


def _print_stress(res):
    for loc, s in res.summaries.items():
        print(f"  {loc}: {s['evidence']}")
        print(f"    agreement={s['evaluation']['agreement']:.2f} checks={json.dumps(s['checks'])}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["bare", "stress", "demo"])
    ap.add_argument("--obs")
    ap.add_argument("--weekly")
    ap.add_argument("--out", required=True)
    ap.add_argument("--split", default="year", choices=list(SPLITS))
    ap.add_argument("--loyo", action="store_true", help="[S] leave-one-year-out isolation forest")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    if a.cmd == "bare":
        _print_bare(run_bare_cover(_read(a.obs), a.split, a.out, a.seed))
    elif a.cmd == "stress":
        _print_stress(run_stress(_read(a.weekly), a.out, seed=a.seed, leave_one_year_out=a.loyo))
    else:
        from fieldshift_models.synthetic import synthetic_observations, synthetic_weekly
        print("FAKE synthetic data - smoke test only")
        obs, _ = synthetic_observations(a.seed)
        for sp in ["year", "ca_fallow", "cross_site"]:
            print(f"[B6.1 split={sp}]")
            _print_bare(run_bare_cover(obs, sp, a.out, a.seed))
        print("[B6.2]")
        _print_stress(run_stress(synthetic_weekly(a.seed)[0], a.out, seed=a.seed))


if __name__ == "__main__":
    main()
