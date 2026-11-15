"""This week on the field: `GET /api/locations/{id}/this_week` (7-day irrigation, alerts and field access) and
`GET /api/reach` (how many California acres CropLytics's rice and forage rotations cover). Mounted from app/main.py
with one `include_router` line placed before the anyloc router (its catch-all would otherwise answer pt_* ids).

Location ids: registry presets (CA and BC), tapped points `pt_...` and, through `register_resolver`, any future id
family (the `my_` fields). See resolve.py."""
from .resolve import register_resolver, resolve_location  # noqa: F401
from .router import router  # noqa: F401
