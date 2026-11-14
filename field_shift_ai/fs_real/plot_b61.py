import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

C = {"bare": "#eb6834", "partial": "#2a78d6", "covered": "#1baf7a"}
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

p = pd.concat([pd.read_csv("out/bare_cover_predictions_ca_fallow.csv"),
               pd.read_csv("out/bare_cover_predictions_year.csv")], ignore_index=True)
p["date"] = pd.to_datetime(p["date"])
p = p.sort_values("date")
tr = pd.concat([pd.read_csv("out/bare_cover_transitions_ca_fallow.csv"),
                pd.read_csv("out/bare_cover_transitions_year.csv")], ignore_index=True)
tr["date"] = pd.to_datetime(tr["date"])

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": GRID,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2})
fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 5.6), sharex=True, gridspec_kw={"height_ratios": [2.2, 1.6]},
                             facecolor=SURF)
for a in (a1, a2):
    a.set_facecolor(SURF)
    for s in ("top", "right"):
        a.spines[s].set_visible(False)

# panel 1: NDVI with pseudo-labels
a1.axvspan(pd.Timestamp("2022-01-01"), pd.Timestamp("2022-12-31"), color=GRID, alpha=0.6, lw=0)
a1.text(pd.Timestamp("2022-07-01"), 0.5, "2022 fallow (CDL 61)\ntest year of the\nca_fallow split",
        ha="center", va="center", color=INK2, fontsize=8)
a1.plot(p["date"], p["ndvi"], color=INK2, lw=1.2, zorder=2)
for cls in ("bare", "covered"):
    q = p[p["label"] == cls]
    a1.scatter(q["date"], q["ndvi"], s=26, color=C[cls], edgecolor=SURF, linewidth=1.2, zorder=3,
               label=f"pseudo-label: {cls}")
a1.axhline(0.20, color=C["bare"], lw=1, ls=(0, (3, 3)), label="rule threshold: bare < 0.20")
a1.axhline(0.35, color=C["covered"], lw=1, ls=(0, (3, 3)), label="rule threshold: covered > 0.35")
a1.set_ylabel("NDVI (field median, Sentinel-2)")
a1.set_ylim(-0.35, 1.08)
a1.grid(axis="y", color=GRID, lw=0.8)
a1.legend(loc="upper center", bbox_to_anchor=(0.5, 1.0), frameon=False, fontsize=8, ncol=4)
a1.set_ylim(-0.35, 1.2)
a1.set_title("B6.1 bare-cover detection on real data — Colusa County rice field (39.15 N, 122.10 W), test years only",
             loc="left", color=INK, fontsize=10.5, pad=14)

# panel 2: class strips per method (smoothed), with transitions
rows = [("Rule (NDVI)", "rule_smoothed", "rule"), ("Random forest", "random_forest_smoothed", "random_forest"),
        ("Hist. gradient boosting", "hist_gbt_smoothed", "hist_gbt"), ("Consensus", "consensus_smoothed", "consensus")]
for i, (name, col, meth) in enumerate(rows):
    y = len(rows) - 1 - i
    d = p["date"].values
    for j in range(len(p)):
        x0 = d[j]
        x1 = d[j + 1] if j + 1 < len(p) and (d[j + 1] - d[j]) < pd.Timedelta(days=30) else x0 + pd.Timedelta(days=5)
        c = p[col].iloc[j]
        if isinstance(c, str):
            a2.fill_between([x0, x1], y - 0.36, y + 0.36, color=C[c], lw=0)
    t = tr[tr["method"] == meth]
    for _, e in t.iterrows():
        a2.plot([e["date"]] * 2, [y - 0.45, y + 0.45], color=INK, lw=1.4 if e["type"] == "green_up" else 0.8,
                ls="-" if e["type"] == "green_up" else (0, (2, 2)))
a2.set_yticks(range(len(rows)))
a2.set_yticklabels([r[0] for r in rows][::-1])
a2.tick_params(axis="y", length=0)
a2.spines["left"].set_visible(False)
handles = [Patch(color=C[k], label=k) for k in C] + [
    plt.Line2D([], [], color=INK, lw=1.4, label="green-up"), plt.Line2D([], [], color=INK, lw=0.8, ls=(0, (2, 2)), label="senescence / harvest")]
a2.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=5, frameon=False, fontsize=8)
fig.text(0.01, 0.005, "Sources: ESA Copernicus Sentinel-2 C1 L2A (2022: standard L2A) via Earth Search; USDA NASS CDL via CropScape; "
         "NASA POWER. Labels are Sentinel-2 SCL pseudo-labels, not ground truth.", color=INK2, fontsize=7)
fig.tight_layout(rect=(0, 0.02, 1, 1))
fig.savefig("out/b61_ca_calendar.png", dpi=160, facecolor=SURF)
print("saved")
