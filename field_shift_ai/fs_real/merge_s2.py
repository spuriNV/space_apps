"""Merge Sentinel-2 extracts: Collection-1 L2A for all years except 2022, standard L2A for 2022
(C1 has only ~6 scenes for tile 10SEJ in 2022). Standard-L2A COGs with processing baseline >= 04.00 are
already offset-harmonised on Earth Search, so the -0.1 applied during extraction is added back
(checked against C1 on shared dates: difference ~0.003)."""
import pandas as pd

D = "data/"
c1 = pd.read_csv(D + "fs_s2_ca_colusa_rice.csv", parse_dates=["date"])
c1["collection"] = "sentinel-2-c1-l2a"
l2 = pd.read_csv(D + "fs_s2_ca_colusa_rice_2022_l2a.csv", parse_dates=["date"])
l2["collection"] = "sentinel-2-l2a"
pb = pd.to_numeric(l2["processing_baseline"])
for b in ["blue", "green", "red", "nir", "swir1", "swir2"]:
    l2.loc[pb >= 4, b] += 0.1
m = pd.concat([c1[c1.date.dt.year != 2022], l2], ignore_index=True).sort_values("date")
m.to_csv(D + "fs_s2_ca_colusa_rice_merged.csv", index=False)
print("wrote", D + "fs_s2_ca_colusa_rice_merged.csv", m.shape)
