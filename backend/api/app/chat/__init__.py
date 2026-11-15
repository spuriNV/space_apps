"""Ask CropLytics: a small chat that explains the app and the numbers for the field on screen, in plain words.

Built first for blind and low-vision growers: answers are short plain text (no markdown, units spelled out) so a screen
reader reads them cleanly. `POST /api/chat` and `GET /api/chat/status`, mounted from app/main.py.

Grounding: the browser sends only the question, the last few turns, the field id, the tab and the viewing date. The server
builds the fact sheet itself by calling this app's own routes (so presets, drawn `my_` fields and tapped `pt_` spots all
work) and gives the model only that sheet plus a guide to the app. The model may explain, never advise what to plant or do.

Model: DeepSeek's OpenAI-compatible chat API through httpx (already a dependency). Key: DEEPSEEK_API_KEY from the
environment, or the repo `.env` for local runs. No key: status says disabled, the route returns 503 and the button hides.
Privacy: no chat text is logged or stored; only in-memory request counters.
"""
from __future__ import annotations

import json
import os
import time
from collections import deque
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .facts import build_facts

router = APIRouter()
ROOT = Path(os.environ.get("FIELDSHIFT_ROOT", Path(__file__).resolve().parents[4]))

DEEPSEEK_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/") + "/chat/completions"
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
MAX_Q = 300          # characters per question
MAX_TURN = 800       # characters per earlier turn kept in history
MAX_HISTORY = 6      # earlier turns sent with a question
PER_MIN, PER_HOUR, PER_DAY_ALL = 6, 40, 600


def _key() -> str | None:
    k = os.environ.get("DEEPSEEK_API_KEY")
    if k:
        return k.strip() or None
    env = ROOT / ".env"  # local runs: the repo .env (git-ignored); Render sets the variable instead
    if env.is_file():
        for line in env.read_text().splitlines():
            if line.startswith("DEEPSEEK_API_KEY="):
                v = line.split("=", 1)[1].strip().strip('"').strip("'")
                return v or None
    return None


# ---------- limits (in memory; reset on restart, so the real cap is the spend limit on the DeepSeek account) ----------
_hits: dict[str, deque] = {}
_day = {"date": "", "n": 0}


def _client_ip(req: Request) -> str:
    fwd = req.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (req.client.host if req.client else "?")


def _check_limits(ip: str):
    now = time.time()
    today = time.strftime("%Y-%m-%d")
    if _day["date"] != today:
        _day.update(date=today, n=0)
    if _day["n"] >= PER_DAY_ALL:
        raise HTTPException(429, "The assistant has answered its limit for today. Please try again tomorrow.")
    q = _hits.setdefault(ip, deque())
    while q and now - q[0] > 3600:
        q.popleft()
    if sum(1 for t in q if now - t < 60) >= PER_MIN:
        raise HTTPException(429, "That's a lot of questions at once. Please wait a minute and ask again.")
    if len(q) >= PER_HOUR:
        raise HTTPException(429, "You've reached the hourly limit. Please try again later.")
    q.append(now)
    _day["n"] += 1
    if len(_hits) > 5000:  # keep memory bounded
        for k in [k for k, v in _hits.items() if not v or now - v[-1] > 3600]:
            _hits.pop(k, None)


# ---------- the app guide the model explains from ----------
APP_GUIDE = """\
CropLytics helps California rice and forage growers (and one example field in British Columbia) see what NASA satellites
and other public data say about a field, and compare crop rotations. It explains; it does not decide for the grower.

Layout on a computer: a top bar with, from left to right: the CropLytics name (goes back to all of California), the field
switcher (shows the field picked; open it to search fields by town, county or crop), section tabs, the Viewing date
control, Map layers, and the Ask button for this assistant. A map fills the rest. On a phone the sections are tabs at the
bottom of the screen, the field details are a sheet that slides up from the bottom, and the date control and Map layers
are inside the Menu button at the top right.

Sections (tabs):
- Field now: what is growing, rain since 1 October compared with normal, the yearly water need compared with the water
  limit, soil moisture and groundwater compared with usual for the time of year, and what the soil is like. Below that are
  next steps and a More detail button for the satellite sources, the machine learning check, stress weeks and more.
- Coming season: winter rain and temperature outlook from NOAA (an outlook, not a forecast), water supply (reservoirs,
  snow, drought), and next season's water need.
- This field's year: a strip for each year showing when the field was bare, partly covered, covered by crop, or flooded,
  with events like the 2022 drought and 2023 floods. It can replay the seasons.
- Compare: today's rotation against the alternatives, in acre-feet of water per acre and days of bare soil. The water
  limit here is an example; the grower can change it to their own.
- Print for your adviser: a one-page summary of the chosen rotation to take to a crop adviser.

Other things: pick a field from the list or the map, tap any spot on farmland to analyse it, or draw your own field
outline (rectangle, circle, freehand) to analyse it. The Viewing date control shows the field at earlier dates, such as
the 2022 drought or 2023 floods. Map layers turn satellite layers on and off (HLS greenness, SMAP soil moisture, GRACE
groundwater, IMERG rain, MODIS, ECOSTRESS). Zoom in far on a field to see a 3D view of what is under it.

Data words: greenness (NDVI) runs 0 to 1; below 0.2 counts as bare soil, above 0.6 is a full canopy. A percentile for
soil moisture or groundwater compares today with the same time of year in past years: 50 is typical, 0 the driest on
record, 100 the wettest. Water need is in acre-feet per acre per year (one acre-foot per acre is one foot of water over
the field). Rotation scores are a rule of thumb from 0 to 100, not a model of yield or profit. Example numbers are
placeholders, not live readings. Estimated means modelled, not measured.
"""

SYSTEM = """\
You are the assistant inside CropLytics. Many people using you are blind or have low vision and hear your answers
through a screen reader, and many are farmers who are not data experts.

How to answer:
- Plain spoken English. One to four short sentences, under about 70 words, unless the person asks for more detail.
- Plain text only: no markdown, no asterisks, no bullet symbols, no tables, no emoji, no links.
- Spell out units the way you would say them: "inches", "acre-feet per acre", "degrees Fahrenheit", "percent".
  Round sensibly (one decimal at most). Give a number its meaning ("60th percentile, about normal for November").
- When asked where something is on screen, describe it in words a screen reader user can act on: which bar, tab or
  button, and its name. Never say "click the green button" or rely on colour or position alone.
- Use only the facts and the app guide below. If the facts do not hold the answer, say you do not have that number and,
  if it helps, name the section of the app where it might be.
- Never invent numbers. Every number you say must come from the facts or the app guide.
- You explain; you do not advise. Do not tell anyone what to plant, when to irrigate, how much water to use, or which
  fertiliser or pesticide to apply, and give no legal, water-rights or insurance advice. For those, say briefly that it
  is a question for their crop adviser or local extension office, and offer what the numbers show instead.
- Outlooks are not forecasts; say so if asked about the weather ahead.
- If no field is picked, help the person learn the app and tell them how to pick a field.
"""


class Turn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[Turn] = Field(default_factory=list)
    field_id: str | None = Field(None, max_length=120)
    screen: str | None = Field(None, max_length=40)   # the tab or panel open: now, season, year, compare, brief, fields
    date: str | None = Field(None, max_length=40)     # the Viewing date label, e.g. "Today, mid Nov 2026"
    water_limit: float | None = Field(None, ge=0, le=20)  # acre-feet per acre set on screen (example unless changed)


@router.get("/api/chat/status")
def chat_status():
    return {"enabled": _key() is not None}


@router.post("/api/chat")
async def chat(body: ChatRequest, req: Request):
    key = _key()
    if not key:
        raise HTTPException(503, "The assistant is not switched on for this site.")
    q = body.question.strip()
    if not q:
        raise HTTPException(422, "Please type a question.")
    if len(q) > MAX_Q:
        raise HTTPException(422, f"Please keep questions under {MAX_Q} characters.")
    _check_limits(_client_ip(req))

    facts = await build_facts(body.field_id, body.water_limit) if body.field_id else {"field": None, "note": "No field is picked yet."}
    screen = {"tab_open": body.screen or "unknown", "viewing_date": body.date or "today"}
    context = (APP_GUIDE + "\nWhat the person has open now: " + json.dumps(screen) +
               "\n\nFacts for the field on screen (JSON; null or missing means not available):\n" +
               json.dumps(facts, ensure_ascii=False, separators=(",", ":")))
    msgs: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM + "\n\n" + context}]
    for t in body.history[-MAX_HISTORY:]:
        msgs.append({"role": t.role, "content": t.content[:MAX_TURN]})
    msgs.append({"role": "user", "content": q})

    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(DEEPSEEK_URL, headers={"Authorization": f"Bearer {key}"},
                             json={"model": MODEL, "messages": msgs, "max_tokens": 400, "temperature": 0.3})
    except httpx.HTTPError:
        raise HTTPException(502, "The assistant could not be reached. Please try again.")
    if r.status_code != 200:
        # never echo the provider's body: it can include account details
        raise HTTPException(502, f"The assistant had a problem (code {r.status_code}). Please try again.")
    try:
        answer = r.json()["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, ValueError):
        raise HTTPException(502, "The assistant gave an empty answer. Please try again.")
    return {"answer": _plain(answer), "field_name": (facts.get("field") or {}).get("name")}


def _plain(s: str) -> str:
    """Strip markdown a model may still emit, so screen readers do not read out symbols."""
    import re
    s = re.sub(r"\*\*|__|`|^#+\s*", "", s, flags=re.M)
    s = re.sub(r"^\s*[-*•]\s+", "", s, flags=re.M)
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()
