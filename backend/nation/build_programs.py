"""Writes backend/nation/programs.json from the table below (programs from docs/nation-tools-research.md PART B section 3).
Edit PROGRAMS here (or programs.json directly) and re-run: python3 backend/nation/build_programs.py. Stdlib only.

jurisdiction: US = US federal; CA = California; CAN = Canada federal; BC = British Columbia.
verified: true only when the research report read the program's own page for who/what/status; false when any of those rests
on snippets or a page that did not load. status_note says what the status rests on. url_checked = date the report opened it.
"""
import json
from pathlib import Path

CHECKED = "2026-11-15"
S = ["field_outline", "drought_history", "water_baseline", "rotation_comparison", "water_context", "sources_caveats"]
P = []


def add(id, name, agency, jur, eligible, funds, amount, status, deadline, url, verified, helps, sections, note="", reasons=None):
    P.append({"id": id, "name": name, "agency": agency, "jurisdictions": jur, "eligible": eligible, "funds": funds,
              "typical_amount": amount, "status": status, "deadline": deadline, "status_note": note, "url": url,
              "url_checked": CHECKED, "verified": verified, "how_croplytics_helps": helps, "report_sections": sections,
              "reasons": reasons or {}})


add("nasa_ipi", "NASA Indigenous Peoples Initiative (Earth Action)", "NASA", ["US", "CA", "BC", "CAN"],
    "Federally recognized tribes and Indigenous communities (as listed partners)", "Training and co-developed workshops, not grants", "n/a",
    "rolling", None, "https://science.nasa.gov/earth-science/earth-action", True,
    "A NASA-data tool that could be used in trainings; not a funding route.", ["sources_caveats"], "ongoing per NASA page")
add("nasa_develop", "NASA DEVELOP", "NASA", ["US", "CA", "BC", "CAN"], "Partner organizations, tribes included", "10-week feasibility projects at no cost to the partner", "n/a",
    "unknown", None, "https://develop.larc.nasa.gov/", False,
    "A starting point for a DEVELOP project.", ["drought_history", "sources_caveats"], "term-based; develop.larc.nasa.gov did not load for the researcher")
add("nasa_arset", "NASA ARSET training", "NASA", ["US", "CA", "BC", "CAN"], "Open to anyone", "Free online training", "free",
    "rolling", None, "https://www.earthdata.nasa.gov/data/projects/arset", True,
    "Capacity building for staff who will read satellite data.", ["sources_caveats"], "catalogue live")
add("nasa_wwao", "NASA Western Water Applications Office (WWAO)", "NASA / JPL", ["US", "CA"], "Western US water managers", "Co-developed tools (for example the Navajo drought severity tool)", "n/a",
    "rolling", None, "https://wwao.jpl.nasa.gov/water-portfolio/water-projects/nasa-navajo-drought-severity-tool-user-guide", True,
    "A precedent for a tribal water tool built on NASA data.", ["drought_history", "sources_caveats"], "ongoing")
add("eqip", "USDA NRCS EQIP", "USDA NRCS", ["US", "CA"], "Producers, including tribes (tribes may get a higher payment rate and advance payment)",
    "Conservation practices such as irrigation water management and cover crops", "Per-practice payment schedules; the underserved rate is at least 25% above base",
    "rolling", "continuous sign-up; state ranking dates apply", "https://www.nrcs.usda.gov/programs-initiatives/eqip-environmental-quality-incentives", False,
    "The report gives baseline crop water use, erosion and soil-cover figures per rotation; a cover-crop rotation maps to practice 340 and water-saving to 449.",
    ["field_outline", "water_baseline", "rotation_comparison", "sources_caveats"], "tribal payment-rate claim is from an NRCS Idaho page; the national page did not load for the researcher",
    {"default": "Cover-crop and water-saving rotations compared here map to EQIP practices 340 and 449."})
add("usda_iag", "USDA Indigenous Animals Harvesting and Meat Processing Grant", "USDA", ["US", "CA"], "Tribes", "Meat processing", "Up to $50M total (ARPA); FY23 awards about $42M",
    "unknown", "no 2026 round found", "https://www.usda.gov/iag", False,
    "Weak fit: forage and range greenness for herd planning only.", ["field_outline", "drought_history", "sources_caveats"], "FY23 round closed 19 Jul 2023; page returned 403")
add("nifa_frtep", "USDA NIFA Federally Recognized Tribes Extension Program (FRTEP)", "USDA NIFA", ["US", "CA"], "Land-grant universities (extension on reservations)",
    "Farm and ranch productivity, natural resources", "Not listed; past funding over $3.8M", "unknown", "see the current NOFO",
    "https://www.nifa.usda.gov/grants/programs/federally-recognized-tribes-extension-program", True,
    "A tool extension agents can use with tribal farms.", ["field_outline", "rotation_comparison", "sources_caveats"], "check the NOFO")
add("usda_otr", "USDA Office of Tribal Relations", "USDA", ["US", "CA"], "Tribes", "Coordination and referral, not grants", "n/a",
    "rolling", None, "https://www.usda.gov/tribalrelations", False, "A referral path.", ["sources_caveats"], "page returned 403 to the researcher")
add("bia_tcr", "BIA Tribal Community Resilience Annual Awards", "BIA", ["US", "CA"], "Federally recognized tribes and tribal organizations", "Competitive resilience funding", "Not listed",
    "unknown", None, "https://www.bia.gov/service/tcr-annual-awards-program", True,
    "Drought and climate history plus rotation scenarios for an adaptation-planning narrative.", ["drought_history", "water_baseline", "rotation_comparison", "sources_caveats"],
    "BIA page: updates are pending on future funding cycles")
add("bia_wmppd", "BIA Water Management, Planning and Pre-Development Program", "BIA", ["US", "CA"], "Tribes, through the BIA Regional Office",
    "Technical assistance and water surveys including quantification studies", "Not listed", "unknown", "FY27 call reportedly March 2026",
    "https://www.bia.gov/service/water-management-planning-and-pre-development-program", False,
    "ET-based crop water demand and GRACE-DA trends as preliminary characterization of water concerns.", ["field_outline", "drought_history", "water_baseline", "water_context", "sources_caveats"],
    "scope and FY27 call timing are from search snippets, not the program page text",
    {"default": "BIA Water Management funds water surveys and quantification studies; the water baseline and drought history here are preliminary inputs.",
     "ca": "{subbasin}: BIA Water Management funds quantification studies, which fits tribes whose reserved water rights are not yet quantified."})
add("epa_gap", "EPA Indian Environmental General Assistance Program (GAP)", "US EPA", ["US", "CA"], "Federally recognized tribes and consortia", "Environmental program capacity, including monitoring",
    "Region 10 ceiling up to $138k per year; Region 9 not listed", "closed", "Region 9 deadline 6 Feb 2026 (passed)", "https://www.epa.gov/tribal-pacific-sw/r9-gap-funding", False,
    "Water and land monitoring baselines for a workplan.", ["water_baseline", "water_context", "sources_caveats"], "from search results; check the next NOFA")
add("usbr_native", "US Bureau of Reclamation Native American Affairs", "USBR", ["US", "CA"], "Tribes", "Technical assistance on water", "Varies",
    "rolling", None, "https://www.usbr.gov/native/", True, "Water-use estimates.", ["water_baseline", "water_context", "sources_caveats"], "")
add("cdfa_tfs", "CDFA Tribal Food Sovereignty Grant Program", "CDFA", ["CA"], "California Native American Tribes",
    "Food systems (stewardship, cultivation, harvesting, production, distribution) and land return", "$15M total", "unknown",
    "Public comment Nov-Dec 2026; RFP Jan 2027; applications due Mar 2027 (tentative)", "https://www.cdfa.ca.gov/tribal_food_sovereignty/", True,
    "The field report gives drought history, water baseline and a rotation comparison for a food-production proposal.",
    ["field_outline", "drought_history", "water_baseline", "rotation_comparison", "sources_caveats"], "not yet open; dates tentative per CDFA",
    {"default": "Funds tribal food systems; the report gives the drought history, water baseline and rotation plan for a production proposal."})
add("sgc_tcb", "SGC Tribal Capacity Building Program, Round 2", "California Strategic Growth Council", ["CA"], "California tribes on the NAHC list",
    "Staff salaries, planning and pursuing climate funding", "$350k to $420k over 3 years", "closed", "closed 11 Aug 2026", "https://sgc.ca.gov/grant-programs/tribal", True,
    "A no-cost tool that adds to a funded staff member's capacity.", ["sources_caveats"], "awards were scheduled for 28 Oct 2026")
add("cnra_tnbs", "CNRA Tribal Nature-Based Solutions", "California Natural Resources Agency", ["CA"], "California tribes", "Land acquisition and return, and stewardship", "2026 round about $9.2M (unconfirmed)",
    "unknown", None, "https://resources.ca.gov/", False, "A baseline land-cover, water and NDVI profile for a parcel being acquired.",
    ["field_outline", "water_baseline", "sources_caveats"], "resources.ca.gov pages returned 403 to the researcher")
add("dwr_sgma_tribal", "DWR SGMA tribal engagement (guidance and Tribal Advisory Group)", "California DWR", ["CA"], "Tribes", "Guidance and consultation, not money", "n/a",
    "rolling", None, "https://water.ca.gov/About/Tribal-Policy", False, "Groundwater context for a GSA consultation.", ["water_context", "sources_caveats"],
    "page returned 403 to the researcher",
    {"default": "Groundwater context for a groundwater sustainability agency consultation.", "ca": "{subbasin}: groundwater context to bring to a groundwater sustainability agency consultation."})
add("fndi_ctf", "First Nations Development Institute, California Tribal Fund", "First Nations Development Institute (non-government)", ["CA"], "California Native-led nonprofits and tribal programs",
    "Ancestral lands and waters stewardship", "Not listed", "closed", "2026 deadline 27 Apr 2026 (passed)", "https://www.firstnations.org/programs/california-tribal-fund/", True,
    "Land and water baseline for a stewardship proposal.", ["field_outline", "water_baseline", "sources_caveats"], "")
add("aafc_pathfinder", "AAFC Indigenous Pathfinder Service", "Agriculture and Agri-Food Canada", ["CAN", "BC"], "First Nations, Metis and Inuit individuals and organizations",
    "Advice and referral to AAFC programs", "n/a", "open", None, "https://agriculture.canada.ca/en/programs/indigenous-pathfinder-service", True,
    "The report as a project summary for the advisor.", ["field_outline", "water_baseline", "rotation_comparison", "sources_caveats"], "")
add("fn_adapt", "CIRNAC First Nation Adapt", "Crown-Indigenous Relations and Northern Affairs Canada", ["CAN", "BC"], "First Nations south of 60 degrees",
    "Risk assessments, hazard mapping, adaptation in land-use planning", "$8.42M available for FY2026-27", "rolling", "open year-round",
    "https://www.rcaanc-cirnac.gc.ca/eng/1481305681144/1594738066665", True,
    "Drought, flow-order and fire history to inform land-use and adaptation planning.", ["field_outline", "drought_history", "water_baseline", "water_context", "sources_caveats"], "",
    {"default": "Funds adaptation risk assessments and land-use planning; the drought history and water context here are inputs.",
     "bc": "{watershed}: First Nation Adapt funds drought risk assessment and adaptation planning, and is open year-round."})
add("cirnac_icbcm", "CIRNAC Indigenous Community-Based Climate Monitoring", "CIRNAC", ["CAN", "BC"], "Indigenous communities and Nations", "Monitoring plans, staff and equipment", "Not listed",
    "rolling", "no deadline; 2026-28 south-of-60 funding prioritizes previous recipients and referrals", "https://www.rcaanc-cirnac.gc.ca/eng/1509728370447", True,
    "Satellite baselines that sit beside community-run cameras and gauges.", ["drought_history", "water_context", "sources_caveats"], "")
add("dfo_bcsrif", "BC Salmon Restoration and Innovation Fund", "DFO / Province of BC", ["CAN", "BC"], "Indigenous groups and others", "Salmon habitat", "Not listed",
    "closed", "supports projects to 31 Mar 2026", "https://www.dfo-mpo.gc.ca/fisheries-peches/initiatives/fish-fund-bc-fonds-peche-cb/index-eng.html", True,
    "Not applicable now.", ["water_context", "sources_caveats"], "")
add("fcc_indigenous", "FCC Indigenous financing", "Farm Credit Canada", ["CAN", "BC"], "Indigenous producers", "Loans", "Varies",
    "rolling", None, "https://www.fcc-fac.ca/en/financing/indigenous-financing", True, "Rotation water and cover context for a lending conversation.",
    ["field_outline", "rotation_comparison", "sources_caveats"], "")
add("iaf_ifsap", "IAF / AAFC-BC Indigenous Food Systems and Agriculture Partnership Program (IFSAP)", "Indigenous Agriculture and Food (IAF) BC / AAFC", ["BC"], "BC Indigenous Nations and organizations",
    "Agriculture, food processing, planning", "Up to $80k", "closed", None, "https://iafbc.ca/wp-content/uploads/2022/09/IFSAP-Program-Guide_Web_Sept_FINAL.pdf", False,
    "Not applicable now.", ["sources_caveats"], "appears closed; the program page returned 404")
add("bc_food_pathways", "BC Indigenous Food Pathways Program", "Province of BC", ["BC"], "BC Indigenous groups", "Food projects", "Up to 75% of costs, maximum $200k",
    "closed", "intake deadline was 10 Jan 2025", "https://www2.gov.bc.ca/gov/content/industry/agriculture-seafood", False, "Not applicable now.", ["sources_caveats"],
    "program page returned 404; this link is the provincial agriculture landing page, not the program")
add("nrt_ifss", "NRT Indigenous Food Security and Sovereignty Grant", "New Relationship Trust", ["BC"], "BC First Nations, departments and Indigenous farms",
    "Planning (Stream 1) and capital (Stream 2)", "Up to $150k (Stream 1) and $250k (Stream 2)", "closed", "closed; funds exhausted",
    "https://newrelationshiptrust.ca/indigenous-food-security-and-sovereignty/", True, "Baseline for a future intake.", ["field_outline", "water_baseline", "rotation_comparison", "sources_caveats"], "")
add("iaf_isat", "IAF Indigenous Skills and Training (ISAT)", "Indigenous Agriculture and Food (IAF) BC", ["BC"], "BC Indigenous groups", "Skills and training", "Not listed",
    "closed", "not accepting applications", "https://iafbc.ca/indigenous-food-systems-and-agriculture-skills-and-training-program/", True, "Not applicable now.", ["sources_caveats"], "")

out = {"about": "Funding programs relevant to First Nations and tribal farms, lands and water staff. Source: docs/nation-tools-research.md PART B section 3. "
                "Statuses were read on the url_checked date and change; verify on the program page before applying. verified=false means a key fact "
                "(status, scope or amount) rests on search results or a page that did not load. Edit via build_programs.py or this file.",
       "as_of": CHECKED, "programs": P}
Path(__file__).with_name("programs.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
print(len(P), "programs")
