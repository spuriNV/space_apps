"""Item 7: expected 2027 irrigation need per rotation, via backend/engine score(). Run with the engine's env:
   cd backend/engine && uv run python ../outlook/src/irrigation.py"""
import json, sys, datetime as dt
from pathlib import Path
from rotation_engine import score
OUT = Path(__file__).resolve().parents[1] / "out"
fetched = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
hist = json.loads((OUT / "history.json").read_text())
res = {"fetched_at": fetched, "label": "Outlook scenario, not a forecast", "presets": {}}
for pid, h in hist["presets"].items():
    sc = h["scenario"]; runs = {}
    for k in ("low", "mid", "high"):
        sc_in = {"dT_c": sc["dT_c"][k], "dP_pct": sc["dP_pct"][k]}
        runs[k] = (sc_in, score(pid, scenario=sc_in))
    strategies = []
    for i, base in enumerate(runs["mid"][1]):
        vals = {k: runs[k][1][i]["water"]["irrigation_need_af_ac"] for k in runs}
        v = {k: vals[k]["value"] for k in vals}
        strategies.append({"id": base["id"], "name": base["name"], "is_baseline": base["is_baseline"],
            "irrigation_need_af_ac": {"value": v["mid"], "low": min(v.values()), "high": max(v.values()), "unit": "acre-ft/acre/yr", "method": "model", "fetched_at": fetched, "verified": False,
                "source": {"id": "field_shift_engine", "title": "Field Shift rotation engine score(), scenario from CPC outlook", "url": "backend/engine/README.md", "accessed": fetched, "verified": False},
                "note": "value = CPC-weighted scenario; low/high = lowest/highest of {climatology, CPC-weighted, favoured-category-fully-realised} runs. Engine's own parameter range (Kc, ETo +/-15%, rice F, precip source) at the CPC-weighted run is in engine_param_range."},
            "engine_param_range": {"low": vals["mid"]["low"], "high": vals["mid"]["high"]},
            "scenario_values": v,
            "change_vs_default_pct": round(100 * (v["mid"] - v["low"]) / v["low"], 1) if v["low"] else None,
            "allocation_check": runs["mid"][1][i]["water"]["allocation_check"]})
    res["presets"][pid] = {"scenarios": {k: runs[k][0] for k in runs}, "default_is": "scenario 'low' = climatology (dT 0, dP 0)",
        "allocation_note": "No default allocation exists in the repo (spec: user input, acre-ft/acre). Compared with the engine's default-weather run instead; an allocation is never assumed.", "strategies": strategies}
    for s in strategies:
        print(pid, s["id"], s["scenario_values"], s["irrigation_need_af_ac"]["low"], s["irrigation_need_af_ac"]["high"])
(OUT / "irrigation.json").write_text(json.dumps(res, indent=1))
