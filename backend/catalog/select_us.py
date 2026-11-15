"""US outside California for the farm catalog: ~215 real fields across ten farm regions.

Outlines: USDA NASS Crop Sequence Boundaries (CSB) 2016-2023 rev23 (national file geodatabase; each polygon is a field-sized
area of one crop sequence). A field qualifies when its CSB area is 20-300 acres, it was cropland in >= 7 of the 8 years, and
its 2023 Cropland Data Layer class is one of the region's target crops. Names come from the two most frequent crops of the
sequence ("Corn and soybean field near Ames, Story County, IA"). Farthest-point spread, every pair >= 5 km apart (and from
the California and Canadian fields). The CSB polygon (simplified to ~12 m) is the field outline the build uses.
Place names: US Census TIGERweb places.

Merges into out/selection.json (keeps everything whose region does not start with us-). Download the zip once:
https://www.nass.usda.gov/sites/default/files/Research_and_Science/Crop-Sequence-Boundaries/datasets/NationalCSB_2016-2023_rev23.zip
Run: cd backend/catalog && uv run python select_us.py --gdb /path/to/CSB1623.gdb
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("sel0", HERE / "select.py")
S = importlib.util.module_from_spec(spec)
sys.modules["sel0"] = S
spec.loader.exec_module(S)

ST = {"19": "IA", "17": "IL", "18": "IN", "31": "NE", "27": "MN", "20": "KS", "38": "ND", "46": "SD", "40": "OK", "48": "TX",
      "05": "AR", "28": "MS", "22": "LA", "13": "GA", "01": "AL", "37": "NC", "53": "WA", "41": "OR", "16": "ID", "08": "CO",
      "30": "MT", "49": "UT", "04": "AZ", "35": "NM", "42": "PA", "36": "NY", "12": "FL", "26": "MI", "55": "WI"}
# region -> (area label, states, {group: (n, CDL codes, optional (lon0, lat0, lon1, lat1) box for TX)})
PANHANDLE = (-103.1, 33.5, -99.9, 36.6)
PLAN = {
    "us-midwest": ("Corn Belt", ["19", "17", "18", "31", "27"], {"grain": (15, {1}, None), "soy": (15, {5}, None)}),
    "us-plains": ("Great Plains", ["20", "38", "46", "40", "48"], {"grain": (14, {22, 23, 24}, None), "sorghum": (8, {4}, None), "cotton": (3, {2}, PANHANDLE), "soy": (3, {5}, None)}),
    "us-delta": ("Mississippi Delta", ["05", "28", "22"], {"rice": (8, {3}, None), "cotton": (6, {2}, None), "soy": (8, {5}, None)}),
    "us-southeast": ("Southeast", ["13", "01", "37"], {"cotton": (11, {2}, None), "peanuts": (11, {10}, None)}),
    "us-northwest": ("Pacific Northwest", ["53", "41", "16"], {"grain": (8, {24}, None), "potatoes": (6, {43}, None), "hops": (4, {56}, None), "orchard": (8, {68, 66}, None)}),
    "us-mountain": ("Mountain West", ["08", "30", "49"], {"forage": (10, {36}, None), "grain": (10, {21, 23}, None)}),
    "us-southwest": ("Desert Southwest", ["04", "35"], {"cotton": (8, {2}, None), "forage": (8, {36}, None)}),
    "us-northeast": ("Northeast and Mid-Atlantic", ["42", "36"], {"forage": (10, {36, 37}, None), "grain": (8, {1}, None)}),
    "us-florida": ("Florida", ["12"], {"citrus": (8, {212, 72}, None), "vegetables": (6, {54, 50, 216, 48, 12, 47, 2}, None)}),
    "us-greatlakes": ("Great Lakes", ["26", "55"], {"forage": (8, {36, 37}, None), "orchard": (6, {66}, None), "grain": (6, {1}, None)}),
}
LABEL = {"grain": "Corn and grain", "soy": "Soybeans", "sorghum": "Sorghum", "cotton": "Cotton", "rice": "Rice", "peanuts": "Peanuts",
         "potatoes": "Potatoes", "hops": "Hops", "orchard": "Tree fruit", "forage": "Alfalfa, hay and pasture", "citrus": "Citrus",
         "vegetables": "Tomatoes, vegetables and berries"}
NOUN = {1: "corn", 5: "soybean", 4: "sorghum", 2: "cotton", 3: "rice", 10: "peanut", 22: "durum wheat", 23: "spring wheat",
        24: "winter wheat", 21: "barley", 36: "alfalfa", 37: "hay", 43: "potato", 56: "hop", 28: "oat", 12: "sweet corn", 6: "sunflower",
        41: "sugarbeet", 42: "dry bean", 53: "pea", 54: "tomato", 50: "cucumber", 216: "pepper", 48: "watermelon", 47: "vegetable",
        61: "fallow", 25: "small grain", 26: "wheat and soybean", 176: "pasture", 58: "clover", 59: "grass seed", 60: "grass hay"}
FIELDCROP = {1, 5, 4, 2, 3, 10, 22, 23, 24, 21, 36, 37, 43, 28, 6, 41, 42, 53, 25, 58}
FINAL = {68: "Apple orchard", 66: "Cherry orchard", 56: "Hop field", 212: "Orange grove", 72: "Citrus grove", 3: "Rice field",
         36: "Alfalfa field", 37: "Hay field", 43: "Potato field", 2: "Cotton field", 10: "Peanut field", 4: "Sorghum field",
         54: "Tomato field", 50: "Cucumber field", 216: "Pepper field", 48: "Watermelon field", 12: "Sweet corn field",
         47: "Vegetable field", 21: "Barley field", 23: "Spring wheat field", 24: "Winter wheat field", 22: "Durum wheat field"}
MIN_SEP = 5.0


def cropland(c):
    return (1 <= c <= 60) or c == 61 or (66 <= c <= 77) or (204 <= c <= 254)


def crop_word(seq, c23):
    if c23 in FINAL and c23 not in (1, 5):
        base = FINAL[c23]
        if c23 in (36, 37, 43, 2, 3, 10, 4, 21, 23, 24, 22):
            top = [k for k, _ in Counter(c for c in seq if c in FIELDCROP).most_common()]
            if len(top) >= 2 and c23 in (36, 37) and top[1] in (1, 36, 37) and Counter(seq)[top[1]] >= 3:
                return f"{NOUN[top[0]].capitalize()} and {NOUN[top[1]]} field"
        return base
    cnt = Counter(c for c in seq if c in FIELDCROP)
    top = [k for k, n in cnt.most_common() if n >= 2]
    if len(top) >= 2 and cnt[top[1]] >= 3:
        return f"{NOUN[top[0]].capitalize()} and {NOUN[top[1]]} field"
    return f"{NOUN.get(c23, 'crop').capitalize()} field"


def main():
    import pyogrio.raw as R  # noqa: PLC0415
    ap = argparse.ArgumentParser()
    ap.add_argument("--gdb", required=True)
    ap.add_argument("--seed", type=int, default=5)
    a = ap.parse_args()
    cache = Path(a.gdb).parent / "attrs.npz"
    cols = ["CSBID", "CSBACRES", "CNTY", "STATEFIPS", "INSIDE_X", "INSIDE_Y"] + [f"CDL{y}" for y in range(2016, 2024)]
    if cache.exists():
        z = np.load(cache, allow_pickle=True)
        d = {k: z[k] for k in z.files}
    else:
        sts = ",".join(f"'{s}'" for s in ST)
        meta, fids, _g, arrs = R.read(a.gdb, layer="national1623", read_geometry=False, return_fids=True, columns=cols,
                                      where=f"STATEFIPS IN ({sts}) AND CSBACRES>=20 AND CSBACRES<=300")
        d = dict(zip(meta["fields"], arrs))
        d["fid"] = fids
        np.savez(cache, **d)
    n = len(d["fid"])
    print("candidate rows", n)
    cdl = np.stack([d[f"CDL{y}"] for y in range(2016, 2024)], axis=1)
    crop_ok = np.vectorize(cropland)(np.arange(0, 256))[cdl].sum(axis=1) >= 7
    to_ll = Transformer.from_crs("ESRI:102003", "EPSG:4326", always_xy=True)   # CSB is NAD83 Albers (USA Contiguous)
    prev = json.loads(S.OUT.read_text())
    others = [f for f in prev["fields"] if not f["region"].startswith("us-")]
    taken = [tuple(f["pt"]) for f in others]
    rng = random.Random(a.seed)
    picked = []
    for region, (area, fips, groups) in PLAN.items():
        for group, (want, codes, box) in groups.items():
            m = crop_ok & np.isin(d["STATEFIPS"], fips) & np.isin(d["CDL2023"], list(codes))
            idx = np.nonzero(m)[0]
            if box:
                lon, lat = to_ll.transform(d["INSIDE_X"][idx], d["INSIDE_Y"][idx])
                idx = idx[(lon >= box[0]) & (lon <= box[2]) & (lat >= box[1]) & (lat <= box[3])]
            sel = []
            by_state = {}
            for i in idx:
                by_state.setdefault(d["STATEFIPS"][i], []).append(int(i))
            states = [st for st in fips if st in by_state]
            pools = {}
            for st in states:
                ii = by_state[st]
                ii = rng.sample(ii, 3000) if len(ii) > 3000 else ii
                lon, lat = to_ll.transform(d["INSIDE_X"][ii], d["INSIDE_Y"][ii])
                pools[st] = [{"pt": (float(x), float(y)), "i": i} for x, y, i in zip(lon, lat, ii)]
            k = 0
            while len(sel) < want and any(pools.values()) and k < want * 6:   # round-robin over states: every state gets a share
                st = states[k % len(states)]
                k += 1
                got = S.spread_pick(pools[st], 1, taken + [p["pt"] for p in picked] + [c["pt"] for c in sel], rng=rng) if pools[st] else []
                if not got:
                    pools[st] = []
                    continue
                if len(sel) >= 1:   # prefer the point farthest from what is already chosen in this group
                    far = max(pools[st], key=lambda c: min(S.km(c["pt"], q["pt"]) for q in sel + picked if q["pt"] is not None) if True else 0)
                    ok = all(S.km(far["pt"], q) >= MIN_SEP for q in taken + [p["pt"] for p in picked] + [c["pt"] for c in sel])
                    got = [far] if ok else got
                sel.append(got[0])
                pools[st] = [c for c in pools[st] if S.km(c["pt"], got[0]["pt"]) >= MIN_SEP]
            print(f"{region:14s} {group:9s} want {want:2d} cands {len(idx):5d} picked {len(sel)}")
            for c in sel:
                i = c["i"]
                seq = [int(v) for v in cdl[i]]
                picked.append({"region": region, "area": area, "country": "US", "state": ST[d["STATEFIPS"][i]], "crop_group": group,
                               "pt": c["pt"], "fid": int(d["fid"][i]), "county": str(d["CNTY"][i]).title(), "acres": round(float(d["CSBACRES"][i]), 1),
                               "crop_word": crop_word(seq, int(d["CDL2023"][i])), "csbid": str(d["CSBID"][i]),
                               "source": {"csb_id": str(d["CSBID"][i]), "cdl_2016_2023": seq, "outline": "USDA NASS CSB 2016-2023 rev23"}})
    # outlines (one geometry read per field by feature id) and 4-decimal interior point
    for p in picked:
        _m, _f, geom, _d = R.read(a.gdb, layer="national1623", fids=[p["fid"]], columns=[])
        from shapely import from_wkb  # noqa: PLC0415
        g = from_wkb(geom[0])
        g = max(g.geoms, key=lambda q: q.area) if g.geom_type == "MultiPolygon" else g
        g = g.simplify(12, preserve_topology=True)
        ll = transform(to_ll.transform, g) if False else transform(Transformer.from_crs(_m["crs"], "EPSG:4326", always_xy=True).transform, g)
        ip = S.interior(ll)
        p["pt"] = (round((ip or ll.representative_point()).x, 4), round((ip or ll.representative_point()).y, 4))
        p["outline"] = [[round(x, 5), round(y, 5)] for x, y in ll.exterior.coords]
    h = S.Http()
    for p in picked:
        pl = S.place_us(h, *p["pt"])
        p["place"] = pl[0] if pl and pl[1] <= 40 else None
        p["crop_group_label"] = LABEL[p["crop_group"]]
        p["id"] = S.point_id(p["pt"][1], p["pt"][0])
        where = f"{p['county']} {'Parish' if p['state'] == 'LA' else 'County'}, {p['state']}"
        p["name"] = f"{p['crop_word']} near {p['place']}, {where}" if p["place"] else f"{p['crop_word']} in {where}"
        p["county"] = where.rsplit(",", 1)[0]
    ids = [p["id"] for p in picked]
    assert len(ids) == len(set(ids))
    prev["fields"] = others + picked
    S.OUT.write_text(json.dumps(prev, indent=1) + "\n")
    print(len(picked), "US fields", Counter(p["region"] for p in picked))


if __name__ == "__main__":
    main()
