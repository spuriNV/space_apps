"""Help for farmers with disabilities (backend/api/data/disability_programs.json).

  GET /api/help/disability?region=ca|bc   programs for that region (no region: all, each tagged with its regions)
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Response

DATA = Path(__file__).resolve().parents[1] / "data" / "disability_programs.json"
router = APIRouter()


@lru_cache(maxsize=1)
def _load() -> dict:
    return json.loads(DATA.read_text())


@router.get("/api/help/disability")
def disability(resp: Response, region: str | None = Query(None, pattern="^(ca|bc)$")):
    d = _load()
    progs = [p for p in d["programs"] if region is None or region in p["regions"]]
    if not progs:
        raise HTTPException(404, "no programs")
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return {"title": "Farming with a disability", "region": region, "checked": d["checked"], "note": d["note"], "programs": progs, "gaps": d["gaps"], "_source": "real"}
