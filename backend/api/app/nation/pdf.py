"""One-page PDF field report (fpdf2, built-in Helvetica, no images) from the dict made by build_report()."""
from __future__ import annotations

from fpdf import FPDF

SECTION_LABEL = {"field_outline": "Field outline, area and land cover", "drought_history": "Drought history", "water_baseline": "Water-use baseline",
                 "rotation_comparison": "Rotation comparison", "water_context": "River or groundwater context", "sources_caveats": "Sources and caveats"}
INK, MUTED, RULE = (28, 36, 33), (95, 105, 100), (190, 196, 192)


def t(s) -> str:
    s = "" if s is None else str(s)
    for a, b in (("–", "-"), ("—", "-"), ("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("×", "x"), ("≤", "<="), ("≥", ">=")):
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


def f1(x, n=0, dash="-"):
    return dash if x is None else f"{x:.{n}f}"


class Page(FPDF):
    def head(self, text):
        self.set_font("Helvetica", "B", 8.5)
        self.set_text_color(*INK)
        self.set_x(12)
        self.cell(0, 4.2, t(text), new_x="LMARGIN", new_y="NEXT")

    def p(self, text, size=6.8, color=INK, h=3.1):
        self.set_font("Helvetica", "", size)
        self.set_text_color(*color)
        self.set_x(12)
        self.multi_cell(186, h, t(text), new_x="LMARGIN", new_y="NEXT")

    def rule(self):
        self.set_draw_color(*RULE)
        self.line(12, self.get_y() + 0.6, 198, self.get_y() + 0.6)
        self.ln(1.6)

    def table(self, head, rows, widths, size=6.4):
        self.set_x(12)
        self.set_font("Helvetica", "B", size)
        self.set_text_color(*MUTED)
        for h_, w in zip(head, widths):
            self.cell(w, 3.2, t(h_), align="L" if h_ == head[0] else "R")
        self.ln(3.2)
        self.set_font("Helvetica", "", size)
        self.set_text_color(*INK)
        for r in rows:
            self.set_x(12)
            for i, (v, w) in enumerate(zip(r, widths)):
                self.cell(w, 3.0, t(v), align="L" if i == 0 else "R")
            self.ln(3.0)


def render(rep: dict) -> bytes:
    pdf = Page(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(False)
    pdf.set_margins(12, 10, 12)
    pdf.set_title(t(rep["title"]))
    pdf.set_creator("CropLytics")
    pdf.add_page()
    fo = rep["field_outline"]
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*INK)
    pdf.cell(0, 6, t(rep["title"]), new_x="LMARGIN", new_y="NEXT")
    sub = f"{fo['name']}  |  {fo['lat']}, {fo['lon']}  |  generated {rep['generated']}"
    if rep["program"]:
        sub += f"  |  for: {rep['program']['name']} ({rep['program']['agency']}), status {rep['program']['status']}"
    pdf.p(sub, 7, MUTED)
    pdf.p("Prepared for: ______________________________    Prepared by: ______________________________", 7.2)
    pdf.rule()

    # 1 outline
    pdf.head("1. Field outline, area and land cover")
    lc = fo["land_cover"]
    pdf.p(f"Area {f1(fo['area_ha'], 1)} ha ({f1(fo['acres'], 0)} acres). Land status (boundary layer): {fo['land_status']}. "
          f"Land cover: {lc['label'] or 'not available'}" + (f" ({lc['year']}, {lc['source']})" if lc["year"] else "") + ".")
    g = fo.get("geometry")
    if g and g.get("coordinates"):
        ring = g["coordinates"][0] if g["type"] == "Polygon" else g["coordinates"][0][0]
        lons, lats = [p[0] for p in ring], [p[1] for p in ring]
        pdf.p(f"Outline: {len(ring) - 1} vertices, bounding box {min(lats):.4f} to {max(lats):.4f} N, {min(lons):.4f} to {max(lons):.4f} E (full outline in report.json).", 6.4, MUTED)
        # inline outline sketch
        x0, y0, w, hh = 168, 10, 28, 14
        sx = w / max(1e-9, (max(lons) - min(lons)) * __import__("math").cos(__import__("math").radians(lats[0])))
        sy = hh / max(1e-9, max(lats) - min(lats))
        k = min(sx, sy)
        kx = __import__("math").cos(__import__("math").radians(lats[0]))
        pts = [(x0 + (lo - min(lons)) * kx * k, y0 + hh - (la - min(lats)) * k) for lo, la in ring]
        pdf.set_draw_color(*INK)
        pdf.set_line_width(0.3)
        for a, b in zip(pts, pts[1:]):
            pdf.line(a[0], a[1], b[0], b[1])
    pdf.ln(0.8)

    # 2 drought history
    pdf.head("2. Drought history by water year (1 Oct - 30 Sep)")
    hist = rep["drought_history"][-9:]
    if hist:
        rows = [(f"{h['year']}{'*' if h['partial'] else ''}", f1(h["imerg_precip_anom_pct"], 0), f1(h["smap_rootzone_pctl"], 0, "n/c"), f1(h["gracedadm_gw_pctl"], 0, "n/c"), f1(h["power_et0_mm"], 0)) for h in hist]
        pdf.table(["Water year", "IMERG rain vs normal %", "SMAP root-zone pctl", "GRACE-DA groundwater pctl", "POWER ETo mm"], rows, [30, 38, 36, 44, 38])
    else:
        pdf.p("Not computed: NASA POWER did not answer for this location.")
    nc = [k for k, v in rep["series_status"].items() if v["status"] != "real"]
    pdf.p("* partial year. n/c or '-' = not computed" + (f" ({', '.join(nc)}: {rep['series_status'][nc[0]]['reason']})" if nc else "") + ".", 6, MUTED)
    pdf.ln(0.8)

    # 3 water baseline
    wb = rep["water_baseline"]
    pdf.head("3. Water-use baseline")
    pdf.p(f"Baseline rotation: {wb['baseline_rotation'] or 'n/a'}. Crop water use (ETc) {f1(wb['crop_water_use_mm_season'])} mm per year; irrigation need "
          f"{f1(wb['irrigation_need_mm_season'])} mm ({f1(wb['irrigation_need_af_per_acre'], 2)} acre-ft per acre). {wb['note']}")
    pdf.ln(0.8)

    # 4 rotations
    pdf.head(f"4. Rotation comparison (irrigation cut off {wb['cutoff_date']})")
    rows = [((r["name"] or r["id"])[:34], f1(r["water_mm_season"]), f1(r["water_mm_after_cutoff"]), f1(r["share_after_cutoff_pct"]),
             f1(r["erosion_index"], 1), f1(r["soil_cover_pct"]), f1(r["n_fixation_score"])) for r in rep["rotation_comparison"]]
    pdf.table(["Rotation", "Water mm/yr", "After cutoff mm", "After %", "Erosion idx", "Soil cover %", "N-fix score"], rows, [58, 22, 26, 16, 18, 22, 24])
    pdf.p("Engine estimates (rule of thumb): erosion idx = rain-weighted bare days per year; N-fix score 0-100, not kg/ha.", 6, MUTED)
    pdf.ln(0.8)

    # 5 context
    cx = rep["context"]
    pdf.head("5. " + ("Groundwater context" if cx["kind"] == "groundwater" else "River context"))
    if cx["kind"] == "groundwater":
        pdf.p(f"Subbasin: {cx['subbasin'] or 'none found'} ({cx['subbasin_id'] or '-'}). GSAs: {', '.join(cx['gsa_names']) or 'none found'}. SGMA status: {cx['sgma_status'] or 'n/a'}. "
              f"GRACE-DA weekly series: {cx['grace_status']}. {cx['caveat']}")
    else:
        pdf.p(cx["text"])
    pdf.ln(0.8)

    # program sections
    if rep["program"]:
        pdf.head("Sections this program asks for (as covered above)")
        pdf.p("; ".join(SECTION_LABEL.get(s, s) for s in rep["report_sections"]) + f".  Program page: {rep['program']['url']}", 6.6)
        if not rep["program"]["verified"]:
            pdf.p("Program details are unverified in our research: confirm status, eligibility and amounts on the program page.", 6.4, MUTED)
        pdf.ln(0.8)

    # sources and caveats
    pdf.head("Sources and caveats")
    pdf.p("Sources: " + "; ".join(f"{s['title']} <{s['url']}>" for s in rep["sources"]), 5.6, MUTED, 2.6)
    pdf.p("Caveats: " + " ".join(rep["caveats"]), 5.6, MUTED, 2.6)
    pdf.p("Planning aid from public satellite and agency data; not legal, water-rights or engineering advice. Check numbers with your own records.", 5.6, MUTED, 2.6)
    if pdf.get_y() > 290:
        raise RuntimeError("report overflowed one page")
    return bytes(pdf.output())
