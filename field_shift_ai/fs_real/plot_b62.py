import json
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
SEQ = {"none": "#e4e3df", "one": "#86b6ef", "both": "#1c5cab"}  # sequential blue: none < one < both
w = pd.read_csv("out/stress_weekly_flags.csv", parse_dates=["week_start"])
summ = json.load(open("out/stress_summary.json"))["ca_colusa_rice"]
years = sorted(w["year"].unique())

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": GRID,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2})
fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 6.2), gridspec_kw={"height_ratios": [1.5, 2]}, facecolor=SURF)
for a in (a1, a2):
    a.set_facecolor(SURF)
    for s in ("top", "right"):
        a.spines[s].set_visible(False)

# panel 1: vulnerability strip, one row per year, x = ISO week
for i, yr in enumerate(years):
    g = w[w["year"] == yr]
    for _, r in g.iterrows():
        a1.add_patch(plt.Rectangle((r["iso_week"] - 0.45, i - 0.38), 0.9, 0.76, color=SEQ[r["strip"]], lw=0))
a1.set_yticks(range(len(years)))
a1.set_yticklabels([f"{y}{'  (fallow)' if y == 2022 else ''}" for y in years])
a1.set_ylim(len(years) - 0.5, -0.5)
a1.set_xlim(17, 41)
months = {18: "May", 22: "Jun", 27: "Jul", 31: "Aug", 36: "Sep", 40: "Oct"}
a1.set_xticks(list(months))
a1.set_xticklabels(list(months.values()))
a1.tick_params(length=0)
a1.legend(handles=[Patch(color=SEQ[k], label={"both": "both models", "one": "one model", "none": "neither"}[k]) for k in ("both", "one", "none")],
          loc="upper left", bbox_to_anchor=(1.0, 1.0), frameon=False, fontsize=8, title="weeks flagged by", title_fontsize=8)
a1.set_title("B6.2 crop-stress weeks on real data — Colusa County rice, growing season (May–Sep), 2015–2025",
             loc="left", color=INK, fontsize=10.5)

# panel 2: composite z with the stress features, all in-season weeks in time order
w = w.sort_values("week_start")
x = range(len(w))
a2.axhline(1.0, color=INK2, lw=1, ls=(0, (3, 3)))
a2.text(len(w) - 1, 1.05, "z-score flag threshold 1.0", ha="right", va="bottom", color=INK2, fontsize=8)
a2.plot(x, w["composite_z"], color="#2a78d6", lw=1.4, label="composite stress z (z-score method)")
fl = w["flag_iforest"].values
a2.scatter([i for i in x if fl[i]], w["composite_z"].values[fl], s=22, color="#eb6834", edgecolor=SURF, lw=1,
           zorder=3, label="flagged by isolation forest")
ticks = [i for i, (d, yr) in enumerate(zip(w["week_start"], w["year"])) if i == 0 or w["year"].iloc[i - 1] != yr]
a2.set_xticks(ticks)
a2.set_xticklabels([w["year"].iloc[i] for i in ticks])
a2.set_xlim(-1, len(w))
a2.grid(axis="y", color=GRID, lw=0.8)
a2.set_ylabel("composite z  (+ = more stressed)")
a2.legend(loc="upper left", frameon=False, fontsize=8, ncol=2)
a2.set_xlabel("in-season weeks only (gaps between seasons removed)")
import sys
feats = sys.argv[1] if len(sys.argv) > 1 else "MODIS MOD13Q1 NDVI (Planetary Computer), NASA POWER ETo + rain"
fig.text(0.01, 0.03, "Features in this run: " + feats + ".\nUnsupervised (no labelled stress events). 2022 weeks are fallow, not stress.",
         color=INK2, fontsize=7)
fig.text(0.01, 0.005, "Model evidence line: " + summ["evidence"], color=INK2, fontsize=7)
fig.tight_layout(rect=(0, 0.06, 1, 1))
fig.savefig("out/b62_ca_stress.png", dpi=160, facecolor=SURF)
print("saved")
