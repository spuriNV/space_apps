package app.croplytics.domain

import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.contentOrNull

data class NationNear(val nation: String, val area: String, val km: Double, val inside: Boolean)
data class PlaceName(val name: String, val english: String?, val nation: String?, val url: String?, val notConfirmed: Boolean)
data class NationHead(val landStatus: String, val areaName: String?, val sourceUrl: String?, val near: List<NationNear>, val places: List<PlaceName>)

data class RotShare(val name: String, val sharePct: Double, val baseline: Boolean, val dryRank: Int?)
data class CutoffRow(val label: String, val mineUnmet: Double?, val lowest: Double?, val requested: Boolean)
data class DroughtView(val cutoffLabel: String, val rows: List<RotShare>, val scenarios: List<CutoffRow>, val note: String?)

data class LandView(val greenYear: Int?, val greenup: String?, val peak: String?, val fades: String?, val greenReason: String?, val snowOff: String?, val fire7: String?, val links: List<Pair<String, String>>, val note: String?)

data class Program(val id: String, val name: String, val agency: String, val amount: String, val eligible: String, val status: String, val url: String?, val helps: String?, val verified: Boolean)
data class FundingView(val programs: List<Program>, val disclaimer: String?)

data class GroundwaterView(val basin: String, val priority: String?, val agencies: List<String>, val status: String?, val latestPctl: Int?, val reason: String?, val pumping: List<Pair<String, Int>>, val note: String?, val caveat: String?)

data class SalmonView(val lines: List<String>, val flowNow: String?, val window: String?, val windowWhy: String?, val statement: String?)

/** Readers for the Nation tools and salmon routes (NationTools.tsx, Salmon.tsx). Every read tolerates missing fields; a part marked not computed becomes one quiet line. */
object NationLogic {
    private val mon = listOf("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    private val landWords = mapOf(
        "reserve" to "On reserve land", "trust" to "On trust land", "fee" to "On fee land within a reservation",
        "private" to "Not on reserve or trust land", "unknown" to "Land status not known",
        "first_nations_reserve" to "On reserve land", "tribal_land" to "On tribal land",
    )

    private fun JsonElement?.obj(): JsonObject? = this as? JsonObject
    private fun JsonElement?.arr(): JsonArray = this as? JsonArray ?: JsonArray(emptyList())
    private fun JsonElement?.str(): String? = (this as? JsonPrimitive)?.takeIf { it !is JsonNull }?.contentOrNull
    private fun JsonElement?.num(): Double? = (this as? JsonPrimitive)?.takeIf { it !is JsonNull }?.doubleOrNull
    private fun JsonElement?.bool(): Boolean? = (this as? JsonPrimitive)?.booleanOrNull

    fun cap(s: String) = s.replaceFirstChar { it.uppercase() }
    fun mmdd(s: String): String { val p = s.split('-'); val m = p.getOrNull(0)?.toIntOrNull() ?: return s; return "${mon.getOrElse(m - 1) { "" }} ${p.getOrNull(1)?.toIntOrNull() ?: ""}".trim() }
    fun doy(n: Int): String { val d = java.time.LocalDate.ofYearDay(2023, n.coerceIn(1, 365)); return "${mon[d.monthValue - 1]} ${d.dayOfMonth}" }
    fun miles(km: Double) = String.format(java.util.Locale.US, if (km < 16) "%.1f" else "%.0f", km * 0.621)
    /** "SWITSEMALPH INDIAN RESERVE NO. 3" becomes "Switsemalph Indian Reserve No. 3". */
    fun areaName(s: String) = if (s == s.uppercase()) s.lowercase().split(' ').joinToString(" ") { w -> w.replaceFirstChar { it.uppercase() } } else s

    /** The /nation header. Null when the reply has no land status. */
    fun head(o: JsonObject): NationHead? {
        val ls = o["land_status"].obj() ?: return null
        val value = ls["value"].str() ?: return null
        return NationHead(
            landStatus = landWords[value] ?: cap(value.replace('_', ' ')),
            areaName = ls["area_name"].str(),
            sourceUrl = ls["source"].obj()?.get("url").str(),
            near = o["nearest_nations"].arr().mapNotNull { e ->
                val n = e.obj() ?: return@mapNotNull null
                NationNear(n["nation"].str() ?: return@mapNotNull null, areaName(n["nearest_area"].str() ?: ""), n["distance_km"].num() ?: 0.0, n["inside"].bool() == true)
            },
            places = o["place_names"].arr().mapNotNull { e ->
                val p = e.obj() ?: return@mapNotNull null
                PlaceName(p["name"].str() ?: return@mapNotNull null, p["english"].str(), p["nation"].str(), p["source_url"].str(), p["approved_by_nation"].bool() == false)
            },
        )
    }

    fun drought(o: JsonObject): DroughtView? {
        val rots = o["rotations"].arr().mapNotNull { e ->
            val r = e.obj() ?: return@mapNotNull null
            RotShare((r["name"].str() ?: return@mapNotNull null).replace(" (current)", ""), r["share_after_cutoff_pct"].num() ?: return@mapNotNull null, r["is_baseline"].bool() == true, r["dry_year_rank"].num()?.toInt())
        }
        if (rots.isEmpty()) return null
        val baseId = o["rotations"].arr().firstOrNull { it.obj()?.get("is_baseline").bool() == true }?.obj()?.get("id").str() ?: o["rotations"].arr().firstOrNull()?.obj()?.get("id").str()
        val scen = o["cutoff_scenarios"].arr().mapNotNull { e ->
            val s = e.obj() ?: return@mapNotNull null
            val vals = s["rotations"].arr().mapNotNull { it.obj() }.mapNotNull { r -> r["unmet_water_share_pct"].num()?.let { r["id"].str() to it } }
            CutoffRow(mmdd(s["cutoff_date"].str() ?: return@mapNotNull null), vals.firstOrNull { it.first == baseId }?.second, vals.minOfOrNull { it.second }, s["is_requested"].bool() == true)
        }
        return DroughtView(mmdd(o["cutoff_date"].str() ?: ""), rots, scen, o["caveats"].arr().firstOrNull().str())
    }

    fun land(o: JsonObject): LandView {
        val by = o["phenology"].obj()?.get("by_year").arr().mapNotNull { it.obj() }
        val last = by.lastOrNull { it["greenup_doy"].num() != null }
        val snow = o["snow"].obj()
        val f7 = o["fire_detections_7d"].obj()
        val links = o["burn_scars"].arr().mapNotNull { it.obj() }.mapNotNull { b -> b["url"].str()?.let { "Burn scars: ${b["source"].str() ?: "source"}" to it } } +
            o["regs_links"].arr().mapNotNull { it.obj() }.mapNotNull { b -> b["url"].str()?.let { "Regulations: ${b["title"].str() ?: "link"}" to it } }
        return LandView(
            greenYear = last?.get("year").num()?.toInt(),
            greenup = last?.get("greenup_doy").num()?.toInt()?.let(::doy),
            peak = last?.get("peak_doy").num()?.toInt()?.let(::doy),
            fades = last?.get("senescence_doy").num()?.toInt()?.let(::doy),
            greenReason = if (last == null) (o["ndvi_status"].obj()?.get("reason").str()?.let { cap(it).trimEnd('.') + "." } ?: "Not computed for this place.") else null,
            snowOff = if (snow?.get("status").str() == "real") snow?.get("snow_off_doy").num()?.toInt()?.let(::doy) else null,
            fire7 = f7?.let { if (it["status"].str() == "real") "${it["count"].num()?.toInt() ?: 0} within ${miles(it["within_km"].num() ?: 10.0)} mi" else null },
            links = links,
            note = o["harvest_rights_note"].str(),
        )
    }

    fun funding(o: JsonObject): FundingView? {
        val ps = o["programs"].arr().mapNotNull { e ->
            val p = e.obj() ?: return@mapNotNull null
            Program(p["id"].str() ?: return@mapNotNull null, p["name"].str() ?: return@mapNotNull null, p["agency"].str() ?: "", p["typical_amount"].str() ?: "n/a", p["eligible"].str() ?: "",
                p["status"].str() ?: "unknown", p["url"].str(), p["how_croplytics_helps"].str(), p["verified"].bool() != false)
        }
        return if (ps.isEmpty()) null else FundingView(ps, o["disclaimer"].str())
    }

    fun groundwater(o: JsonObject): GroundwaterView? {
        val basin = o["subbasin_title"].str() ?: o["b118_subbasin_name"].str() ?: return null
        val gw = o["gw_pctl_weekly"].arr().mapNotNull { it.obj()?.get("gw_pctl").num() }
        return GroundwaterView(
            basin, o["sgma_priority"].str(), o["gsas"].arr().mapNotNull { it.obj()?.get("name").str() }, o["sgma_status"].str(), gw.lastOrNull()?.toInt(),
            if (gw.isEmpty()) (o["gw_pctl_status"].obj()?.get("reason").str()?.let { cap(it).trimEnd('.') + "." } ?: "Groundwater history is not computed for this place.") else null,
            o["pumping_need_af_by_rotation"].arr().mapNotNull { it.obj() }.mapNotNull { r -> (r["name"].str()?.replace(" (current)", "") ?: return@mapNotNull null) to (r["pumping_need_af"].num()?.toInt() ?: return@mapNotNull null) },
            o["pumping_note"].str(), o["caveat"].str(),
        )
    }

    fun statusWord(s: String) = when (s) { "open" -> "Open"; "rolling" -> "Rolling"; "closed" -> "Closed"; else -> "Check dates" }

    /** Keeps only what the phone shows from /salmon, so the saved copy stays small. */
    fun trimSalmon(o: JsonObject): JsonObject {
        val flow = o["flow"].obj()
        return JsonObject(buildMap {
            o["summary"]?.let { put("summary", it) }
            flow?.get("latest")?.let { put("flow", JsonObject(mapOf("latest" to it))) }
            o["run_timing"].obj()?.get("critical_window")?.let { put("run_timing", JsonObject(mapOf("critical_window" to it))) }
            o["respect"].obj()?.get("statements")?.let { put("respect", JsonObject(mapOf("statements" to it))) }
        })
    }

    fun salmon(o: JsonObject): SalmonView? {
        val lines = o["summary"].arr().mapNotNull { it.str() }
        if (lines.isEmpty()) return null
        val latest = o["flow"].obj()?.get("latest").obj()
        val q = latest?.get("discharge").obj()?.get("value").num()
        val pct = latest?.get("pct_of_mad").obj()?.get("value").num()
        val flow = q?.let { "Right now: ${String.format(java.util.Locale.US, "%.2f", it)} m³/s at the Salmon Arm gauge" + (pct?.let { p -> ", ${p.toInt()}% of the yearly average" } ?: "") + "." }
        val cw = o["run_timing"].obj()?.get("critical_window").obj()
        return SalmonView(lines, flow, cw?.let { "${mmdd(it["from"].str() ?: "")} to ${mmdd(it["to"].str() ?: "")}" }, cw?.get("why").str(), o["respect"].obj()?.get("statements").arr().firstOrNull().str())
    }
}
