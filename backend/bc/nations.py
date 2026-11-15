"""Display names of the Nations for the band names in the BC reserves layer (ADM_INDIAN_RESERVES_BANDS_SP BAND_NAME).

Shared by fetch_reserves.py (reserves_nearby.geojson `nation`) and build_api.py (first_nations.json `nation`). Stdlib only, so
both the bc and the api venvs can import it. Names follow docs/bc-first-nations.md.
"""
NATION = {"Splatsin": "Splatsin", "Neskonlith": "Neskonlith", "Adams Lake": "Adams Lake",
          "Skwlax te Secwepemculecw": "Skwlax te Secwépemc", "Okanagan": "Okanagan Indian Band (Syilx)"}


def nation(band: str | None) -> str | None:
    """The Nation's display name for a band name; the band name itself when it is not in the table."""
    return None if band is None else NATION.get(band, band)
