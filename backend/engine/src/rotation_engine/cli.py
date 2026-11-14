"""CLI: writes backend/engine/out/<preset_id>/strategies.json for default weights.

uv run rotation-engine [preset_id ...] [--allocation AF] [--market sell|feed_own_herd|no_preference]
                       [--replay 2022] [--dT 0] [--dP 0]
"""
from __future__ import annotations

import argparse
import json

from .engine import DEFAULT_WEIGHTS, score
from .weather import CHUNK, PRESETS


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("presets", nargs="*", default=list(PRESETS))
    ap.add_argument("--allocation", type=float, default=None, help="acre-ft/acre per year")
    ap.add_argument("--market", default="no_preference")
    ap.add_argument("--replay", type=int, default=None)
    ap.add_argument("--dT", type=float, default=0.0)
    ap.add_argument("--dP", type=float, default=0.0)
    a = ap.parse_args(argv)
    for pid in a.presets:
        recs = score(pid, DEFAULT_WEIGHTS, {}, a.market, a.allocation, a.replay, {"dT_c": a.dT, "dP_pct": a.dP})
        d = CHUNK / "out" / pid
        d.mkdir(parents=True, exist_ok=True)
        (d / "strategies.json").write_text(json.dumps(recs, indent=1))
        print(f"{pid}: wrote {d / 'strategies.json'}")
        for r in recs:
            c = r["composite"]
            print(f"  {r['id']:32s} composite {c['value']:5.1f} [{c['low']:5.1f}, {c['high']:5.1f}] "
                  f"rank {c.get('rank')} ties {c.get('ties_with')}")


if __name__ == "__main__":
    main()
