package app.croplytics.domain

import app.croplytics.data.remote.dto.LocationDto
import app.croplytics.data.remote.dto.NasaNowDto
import app.croplytics.data.remote.dto.OpenEtDto
import app.croplytics.data.remote.dto.SoilDto
import app.croplytics.data.remote.dto.StrategyDto
import app.croplytics.data.remote.dto.StressDto
import app.croplytics.data.remote.dto.WaterSeenDto
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.doubleOrNull
import kotlin.math.roundToInt

/** One question a grower would ask, with a plain answer (FieldNow.tsx). [moreOnly] answers show only with "More detail" on. */
data class Answer(
    val question: String,
    val headline: String,
    /** Shown always. */
    val detail: String = "",
    /** Shown only with "More detail" on (the web's d-only span). */
    val moreDetail: String = "",
    val cite: String = "",
    val gloss: Gloss? = null,
    val warn: Boolean = false,
    val moreOnly: Boolean = false,
    /** Sand / silt / clay percentages for the soil bar. */
    val soilMix: Triple<Double, Double, Double>? = null,
    /** A plain extra line (soil and rotation). */
    val extra: String? = null,
    /** False while the data behind it is still loading (draw a skeleton). */
    val ready: Boolean = true,
    /** Cover swatch for the growing answer: b p c w u. */
    val swatch: Char? = null,
)

data class Meter(val label: String, val value: String?, val fill: Float?, val mark: Float?, val note: String, val warn: Boolean = false, val spoken: String = "")

data class Glance(
    val year: Int,
    val strip: String,
    val todayStep: Int,
    val state: String?,
    val rain: Meter,
    val need: Meter,
    val green: Meter,
    val soilPct: Int?,
    val gwPct: Int?,
    val soilNote: String,
    val regionalReady: Boolean,
)

data class FieldNowView(val glance: Glance, val answers: List<Answer>)

object FieldNowLogic {
    private fun band(p: Double, hi: String, mid: String, lo: String) = if (p >= 67) hi else if (p > 33) mid else lo
    private fun vsNormal(p: Double?, wet: String, dry: String) = when { p == null -> ""; p >= 115 -> wet; p <= 85 -> dry; else -> "about normal" }
    private fun cap(x: String) = x.replaceFirstChar { it.uppercase() }
    fun mmToAf(mm: Double) = mm / 304.8

    data class Stage(val sw: Char, val text: String, val sub: String)

    fun stage(cal: FieldCalendar, t: Int): Stage {
        val y = cal.at(t) ?: return Stage('u', "No clear satellite view", "Clouds, or no image within 30 days.")
        val d = Timeline.stepOf(t); val c = y.rule[d]; val up = y.greenup; val dn = y.senescence
        return when (c) {
            'w' -> Stage('w', "Under water", if (d >= 30 || d <= 5) "Flooded for the winter, as most years." else "Standing water on the field.")
            'c' -> Stage('c', if (up != null && d >= up && (dn == null || d < dn)) "Crop growing, green since ${Timeline.stepShort(up)}" else "Crop growing, full green cover", "")
            'p' -> Stage('p', "Thin cover", "Some green, less than a full crop: a young crop, regrowth after a cutting, stubble or weeds.")
            'b' -> Stage('b', if (dn != null && d > dn) "Bare since harvest in ${Timeline.stepShort(dn)}" else "Bare ground", "")
            else -> Stage('u', "No clear satellite view", "Clouds, or no image within 30 days.")
        }
    }

    /** OpenET measured use from 1 Jan to the month of t; the latest year with those months if this year is not out yet. */
    data class Measured(val inches: Double, val model: Double, val current: Boolean, val label: String)
    fun measuredSoFar(oet: OpenEtDto?, modelMonths: List<Double>, t: Int): Measured? {
        val rows = oet?.rows?.map { (it.month ?: it.date.take(7)) to (it.etIn ?: (it.etMm ?: 0.0) / 25.4) }.orEmpty()
        if (rows.isEmpty()) return null
        val y = Timeline.yearOf(t); val m = Timeline.stepOf(t) / 3 + 1
        fun sum(yy: Int): Double? { val r = rows.filter { it.first.take(4).toInt() == yy && it.first.substring(5, 7).toInt() <= m }; return if (r.size == m) r.sumOf { it.second } else null }
        var yy = y; var v = sum(y)
        while (v == null && yy > y - 3) { yy--; v = sum(yy) }
        v ?: return null
        return Measured(v, modelMonths.take(m).sum() / 25.4, yy == y, "Jan–${Timeline.MONTHS[m - 1]} $yy")
    }

    val DRIVER = mapOf("z_tmax" to "unusual heat", "z_eto" to "very thirsty air", "z_ndvi" to "weaker growth than in its other years", "iforest" to "an unusual mix of heat, dryness and growth")

    fun stressLine(s: StressDto?, t: Int): String {
        if (s == null || s.weeks.isEmpty()) return "Crop-stress check not loaded"
        val evaluated = s.weeks.filter { it.evaluated == true }.mapNotNull { it.isoYear }.distinct()
        val y = evaluated.filter { it <= Timeline.yearOf(t) }.maxOrNull() ?: return "No growing season checked yet"
        val wk = s.weeks.filter { (it.status == "one" || it.status == "both") && it.weekStart.startsWith("$y") }
        if (wk.isEmpty()) return "No crop-stress weeks in the $y season"
        val top = wk.flatMap { it.drivers }.groupingBy { it }.eachCount().maxByOrNull { it.value }?.key
        return "${wk.size} crop-stress week${if (wk.size == 1) "" else "s"} in the $y season${top?.let { ", mostly ${DRIVER[it] ?: "unusual weather"}" } ?: ""}"
    }

    fun waterLine(w: WaterSeenDto?, regional: RegionalSeries?, t: Int): String {
        val scenes = w?.scenes?.filter { it.clear }?.map { it.date to (it.waterFrac ?: 0.0) }?.takeIf { it.isNotEmpty() } ?: regional?.dswx.orEmpty()
        if (w == null && scenes.isEmpty()) return "Standing-water record not loaded."
        val cut = "%04d-%02d-31".format(Timeline.yearOf(t), Timeline.stepOf(t) / 3 + 1)
        val last = scenes.filter { it.first <= cut }.lastOrNull()
        val seasons = w?.seasons.orEmpty()
        val wet = seasons.count { it.waterSeen == true }; val n = seasons.count { it.clearScenes >= 5 }
        val rec = if (n > 0) " More than half the field was under water in $wet of $n winters with clear views." else ""
        return if (last != null) "NASA OPERA last saw the field clearly on ${Timeline.fmtShort(last.first)}: " +
            (if (last.second >= 0.5) "${(last.second * 100).roundToInt()}% under water" else if (last.second >= 0.1) "water on ${(last.second * 100).roundToInt()}% of it" else "no standing water") + ".$rec"
        else "No clear OPERA view yet.$rec"
    }

    /** Soil facts in plain words (shared.tsx soilFacts). */
    data class SoilFacts(val mix: Triple<Double, Double, Double>?, val texture: String?, val holds: String?, val drains: String?, val salt: String?, val rotation: String?, val source: String)
    private fun known(x: String?) = !x.isNullOrBlank() && !Regex("^(unknown|pending|n/a)$", RegexOption.IGNORE_CASE).matches(x.trim())
    fun soilFacts(s: SoilDto?): SoilFacts {
        val td = s?.textureDetail
        val mix = if (td?.sandPct != null && td.siltPct != null && td.clayPct != null) Triple(td.sandPct, td.siltPct, td.clayPct) else null
        val texture = s?.textureClass?.takeIf(::known)?.lowercase()?.replaceFirstChar { it.uppercase() }
        val inFt = s?.awcMmPerM?.value?.let { it / 1000 * 12 }
        val dc = s?.drainageClass?.takeIf(::known)?.lowercase().orEmpty(); val hg = s?.hydrologicGroup?.takeIf(::known)?.uppercase()?.take(1).orEmpty()
        val drain = if (dc.isEmpty() && hg.isEmpty()) null else if (hg == "D" || "poorly" in dc) "slow" else if ("excessive" in dc || hg == "A") "fast" else "well"
        val ec = s?.ecDsPerM; val salty = ec != null && ec >= 4
        val tl = texture?.lowercase().orEmpty()
        val clayey = (mix?.let { it.third >= 35 } ?: false) || ("clay" in tl && "sandy clay loam" !in tl)
        val sandy = mix?.let { it.first >= 60 } ?: ("sand" in tl)
        val rotation = when {
            salty -> "Salt hurts some crops more than others; check the crop’s salt tolerance with your adviser."
            clayey && (hg == "C" || hg == "D") && drain == "slow" -> "Clay holds water and drains slowly, so it suits flooded rice; slow drainage limits how much a rotation can improve infiltration."
            sandy && inFt != null && inFt < 1.4 -> "Sandy soil holds little water, so crops that need steady moisture take more irrigation here, and flooded rice would lose water downward."
            else -> null
        }
        return SoilFacts(
            mix, texture,
            inFt?.let { "Holds ${Fmt.one(it)} in of water per foot.${if (it < 1.4) " Low." else ""}" },
            drain?.let { when (it) { "slow" -> "Drains slowly."; "fast" -> "Drains fast."; else -> "Drains well." } },
            ec?.let { if (salty) "Salty: ${Fmt.one(it)} dS/m." else "Salt is low." },
            rotation,
            if (s?.awcMmPerM?.source?.id?.contains("soilgrids", true) == true || (dc.isEmpty() && mix != null)) "SoilGrids global soil model (ISRIC), 800 ft squares" else "USDA soil survey (SSURGO), top 3 feet",
        )
    }

    fun calSource(cal: FieldCalendar?) = if (cal?.hls == true) "NASA/USGS HLS satellites (Landsat and Sentinel-2, harmonised by NASA)" else "Landsat (NASA/USGS) and Sentinel-2 satellites"

    fun openetText(strategies: List<StrategyDto>?): String {
        val v = strategies?.firstOrNull { it.isBaseline }?.water?.etcVsOpenetPct?.usable ?: return "Not yet checked against measured water use (OpenET)."
        val r = kotlin.math.abs(v).roundToInt()
        return "Checked against OpenET satellite measurements of this field: our estimate runs about $r% ${if (v >= 0) "high" else "low"}${if (v >= 0) ", as expected for a fully watered crop" else ""}."
    }

    fun etcByMonth(s: StrategyDto?): List<Double> = s?.water?.etcByMonthMm.orEmpty().mapNotNull { e ->
        (e as? JsonPrimitive)?.doubleOrNull ?: ((e as? JsonObject)?.get("value") as? JsonPrimitive)?.doubleOrNull
    }

    fun build(
        loc: LocationDto, cal: FieldCalendar?, regional: RegionalSeries?, nasaNow: NasaNowDto?, strategies: List<StrategyDto>?, daily: Daily?,
        openet: OpenEtDto?, stress: StressDto?, water: WaterSeenDto?, limit: Double?, exampleLimit: Boolean, t: Int, todayT: Int,
        loading: Boolean,
    ): FieldNowView {
        val hist = FieldNames.history(loc)
        val dt = cal?.let { Calendars.latestClearT(it, t) ?: Calendars.dataT(it, t) } ?: t
        val ago = t - dt
        val agoText = if (ago <= 0) "" else if (ago == 1) ", about 10 days ago" else ", about ${(ago * 10.0 / 7).roundToInt()} weeks ago"
        val fs = cal?.let { fieldState(it, dt) }
        val st = cal?.let { stage(it, dt) }
        val yr = Timeline.yearOf(t)
        val base = strategies?.firstOrNull { it.isBaseline }
        val need = base?.water?.irrigationNeedMm
        val needAf = need?.usable?.let(::mmToAf)
        val rain = if (t == todayT && nasaNow?.readings?.get("imerg_wy_to_date_mm")?.value != null && (nasaNow.readings["imerg_wy_to_date_normal_mm"]?.value ?: 0.0) > 0) {
            val mm = nasaNow.readings["imerg_wy_to_date_mm"]!!.value!!; val nm = nasaNow.readings["imerg_wy_to_date_normal_mm"]!!.value!!
            SeasonCalc.RainSoFar(SeasonCalc.Period("1 Oct to ${Timeline.fmtShort(nasaNow.readings["imerg_wy_to_date_mm"]?.obsDate)}", "", "", true), mm / 25.4, nm / 25.4, 25, mm / nm * 100, true)
        } else daily?.let { SeasonCalc.rainSoFar(it, t) }
        val ms = measuredSoFar(openet, etcByMonth(base), t)
        val hf = daily?.let { SeasonCalc.heatFrost(it, t) }
        val cw = if (daily != null && base != null) SeasonCalc.cropWaterSoFar(daily, etcByMonth(base), t) else null
        val sm = regional?.let { latestAt(it.soil, t) }; val smap = sm?.first
        val gr = regional?.let { latestAt(it.groundwater, t) }; val grace = gr?.first
        val behindNote = if (dt < t) " Latest clear view ${Timeline.when_(dt)}$agoText${if (Timeline.yearOf(dt) < yr) "; $yr imagery not processed yet" else ""}." else ""
        val clsOk = fs != null && fs.cls != 'u'

        val glance = Glance(
            year = yr, strip = cal?.year(yr)?.rule ?: "u".repeat(36), todayStep = Timeline.stepOf(t), state = st?.text,
            rain = rain?.let {
                val scale = maxOf(it.inches, it.normal ?: 0.0) * 1.25
                Meter("Rain since 1 Oct", "${SeasonCalc.fmtIn(it.inches)} in", if (it.normal != null && scale > 0) minOf(1.0, it.inches / scale).toFloat() else null,
                    it.normal?.let { n -> if (scale > 0) (n / scale).toFloat() else null }, it.pct?.let { p -> "${p.roundToInt()}% of normal" } ?: "",
                    spoken = "Rain since 1 October: ${SeasonCalc.fmtIn(it.inches)} inches" + (it.normal?.let { n -> ", normal ${SeasonCalc.fmtIn(n)} inches" } ?: ""))
            } ?: Meter("Rain since 1 Oct", null, null, null, ""),
            need = needAf?.let { v ->
                val scale = maxOf(v, limit ?: 0.0) * 1.2
                Meter("Water need, a year", "${Fmt.one(v)} acre-ft/acre", limit?.let { minOf(1.0, v / scale).toFloat() }, limit?.let { (it / scale).toFloat() },
                    limit?.let { "Limit ${Fmt.one(it)}${if (exampleLimit) " (example)" else ""}" } ?: "", warn = limit != null && v > limit,
                    spoken = "Water need ${Fmt.one(v)} acre-feet per acre a year" + (limit?.let { ", limit ${Fmt.one(it)}" } ?: ""))
            } ?: Meter("Water need, a year", null, null, null, ""),
            green = if (clsOk) Meter("Greenness", String.format(java.util.Locale.US, "%.2f", fs!!.ndvi), clamp(fs.ndvi, 0.0, 1.0).toFloat(), 0.6f, cap(Timeline.when_(dt)),
                spoken = "Greenness ${String.format(java.util.Locale.US, "%.2f", fs.ndvi)} on a 0 to 1 scale; above 0.6 is a full canopy") else Meter("Greenness", null, null, null, ""),
            soilPct = smap?.roundToInt(), gwPct = grace?.roundToInt(),
            soilNote = "Soil ${smap?.let { Fmt.ordinal(it.roundToInt()) } ?: "–"}, groundwater ${grace?.let { Fmt.ordinal(it.roundToInt()) } ?: "–"}",
            regionalReady = regional != null,
        )

        val answers = buildList {
            val lastRec = hist.keys.maxOrNull()
            add(Answer(
                "What is growing, and how far along?", st?.text ?: "",
                moreDetail = (if (hist[yr] != null) "${FieldNames.cropName(hist[yr])} on record for $yr." else lastRec?.let { "$yr crop map not published yet (USDA, early ${yr + 1}). $it: ${FieldNames.cropName(hist[it]).lowercase()}." } ?: "") + (st?.sub?.let { " $it" } ?: ""),
                cite = "${calSource(cal)}, 100 ft squares; crop from the USDA Cropland Data Layer.$behindNote", ready = st != null, swatch = st?.sw,
            ))
            add(Answer(
                "How much green cover is there?",
                when { fs == null -> ""; fs.cls != 'u' && fs.cls != 'w' -> if (fs.ndvi >= 0.6) "Full green canopy" else if (fs.ndvi >= 0.35) "Partly green" else if (fs.ndvi >= 0.2) "Thin green cover" else "Little or no green cover"; fs.cls == 'w' -> "Under water, so no green reading"; else -> "No clear view in the last 6 weeks" },
                detail = if (fs != null && fs.cls != 'u' && fs.cls != 'w') "Greenness ${String.format(java.util.Locale.US, "%.2f", fs.ndvi)} on a 0 to 1 scale; above 0.6 is a full canopy." else "",
                cite = "Greenness from ${calSource(cal).replace(" satellites", "")}, field average, ${Timeline.when_(dt)}$agoText.",
                gloss = Gloss.Greenness, moreOnly = true, ready = cal != null,
            ))
            add(rain?.let {
                Answer(
                    "How much rain so far this season?",
                    (if (it.period.current) "" else "No readings for this winter yet. ") + (it.pct?.let { p -> "${if (it.period.current) "So far" else "Last season was"} ${vsNormal(p, "wetter than normal", "drier than normal")}" } ?: ""),
                    detail = "${SeasonCalc.fmtIn(it.inches)} in ${if (it.period.current) "since 1 Oct" else it.period.label}.${it.normal?.let { n -> " Normal: ${SeasonCalc.fmtIn(n)} in." } ?: ""}",
                    cite = "${if (it.imerg) "NASA GPM IMERG satellite rain over the field (one reading for a 6-mile square)" else "NOAA weather stations near the field, averaged"}; normal = the same dates in the ${it.nSeasons} seasons before.",
                )
            } ?: Answer("How much rain so far this season?", "", ready = !loading && daily != null))
            add(when {
                ms != null && ms.current -> Answer(
                    "How much water has the crop used?", "Measured so far this year: ${SeasonCalc.fmtIn(ms.inches)} in",
                    detail = "${ms.label}, measured on this field. Our model for the same months: ${SeasonCalc.fmtIn(ms.model)} in. That is ${Fmt.one(mmToAf(ms.inches * 25.4))} acre-feet per acre.",
                    cite = "OpenET satellite measurement (ensemble of 6 models built on Landsat), monthly, this field’s outline.", gloss = Gloss.Et, moreOnly = true,
                )
                cw != null -> Answer(
                    "How much water has the crop used?", "${if (cw.period.current) "So far this year" else "Last year"}: ${vsNormal(cw.pct, "more than normal", "less than normal")}",
                    detail = "About ${SeasonCalc.fmtIn(cw.inches)} in of water ${cw.period.label}, estimated; normal is ${SeasonCalc.fmtIn(cw.normal)} in. That is ${Fmt.one(mmToAf(cw.inches * 25.4))} acre-feet per acre." +
                        (ms?.let { " Measured on this field by OpenET for ${it.label}: ${SeasonCalc.fmtIn(it.inches)} in (our model for those months: ${SeasonCalc.fmtIn(it.model)} in)." } ?: ""),
                    cite = "Estimate: rotation model driven by NASA POWER sun, wind and humidity${if (ms != null) "; measured: OpenET satellite data, which ends a few months behind" else ""}. ${openetText(strategies)}",
                    gloss = Gloss.Et, moreOnly = true,
                )
                else -> Answer("How much water has the crop used?", if (strategies != null && daily != null) "No rotation model for this field" else "", gloss = Gloss.Et, moreOnly = true, ready = strategies != null && daily != null)
            })
            if (needAf != null) {
                add(Answer(
                    "Will the water limit cover irrigation?",
                    when { limit == null -> "About ${Fmt.one(needAf)} acre-feet per acre a year"; needAf > limit -> "Short by about ${Fmt.one(needAf - limit)} acre-feet per acre"; else -> "Fits your limit in a typical year" },
                    detail = "Needs ${Fmt.one(needAf)} acre-ft/acre a year.${limit?.let { " Limit: ${Fmt.one(it)}." } ?: ""}${if (exampleLimit) " Example, change it on Compare." else ""}",
                    moreDetail = "Likely ${Fmt.one(mmToAf(need.low ?: need.value!!))}–${Fmt.one(mmToAf(need.high ?: need.value!!))} acre-ft/acre.",
                    cite = "Rotation model with NASA POWER weather: crop water use minus rain, typical year 2015–2025.",
                    gloss = Gloss.WaterBalance, warn = limit != null && needAf > limit,
                ))
            } else if (strategies == null) add(Answer("Will the water limit cover irrigation?", "", ready = false))
            add(Answer(
                "Is the soil wetter or drier than usual? And the groundwater?",
                if (regional == null) "" else "${smap?.let { band(it, "Soil wetter than usual", "Soil about normal", "Soil drier than usual") } ?: "No soil reading"}; ${grace?.let { band(it, "more groundwater than usual", "groundwater about normal", "less groundwater than usual").lowercase() } ?: "no groundwater reading"}",
                moreDetail = listOfNotNull(
                    smap?.let { "Soil moisture ${Fmt.ordinal(it.roundToInt())} percentile for the date${if (sm.second < t - 1) " (latest, ${Timeline.when_(sm.second)})" else ""}; 50 is normal." },
                    grace?.let { "Groundwater ${Fmt.ordinal(it.roundToInt())} percentile${if (gr.second < t - 1) " (latest, ${Timeline.when_(gr.second)})" else ""}, whole basin, not your own well." },
                ).joinToString(" "),
                cite = if (regional?.soilSource == "grace_da") "NASA GRACE-FO." else "NASA SMAP and GRACE-FO.",
                gloss = Gloss.SoilAnomaly, ready = regional != null,
            ))
            val soil = soilFacts(loc.soil)
            if (soil.mix != null || soil.texture != null || soil.holds != null || soil.drains != null || soil.salt != null) add(Answer(
                "What is the soil like?", soil.texture ?: "", detail = listOfNotNull(soil.holds, soil.drains, soil.salt).joinToString(" "),
                cite = "${soil.source}.", soilMix = soil.mix, extra = soil.rotation,
            ))
            add(Answer(
                "Has the crop been stressed, or the field under water?", if (loading) "" else stressLine(stress, t),
                detail = if (loading) "" else waterLine(water, regional, t),
                cite = "Crop stress: two statistical methods on satellite greenness and NASA POWER heat and dryness, growing season only. Standing water: NASA OPERA, 100 ft squares, clear images only.",
                gloss = Gloss.Stress, moreOnly = true, ready = !loading,
            ))
            add(hf?.let {
                Answer(
                    "How many hot days and frost nights?",
                    "${it.hot} day${if (it.hot == 1) "" else "s"} at or above ${SeasonCalc.HOT_F} °F ${if (it.period.current) "so far this year" else "in ${it.period.label.replace("last year, ", "")}"}",
                    detail = "Normal for the same dates: ${it.hotNormal?.roundToInt() ?: "?"}. Frost nights (32 °F or lower), ${it.frostPeriod.label}: ${it.frost}; normal ${it.frostNormal?.roundToInt() ?: "?"}.",
                    cite = "NOAA weather stations near the field. NASA POWER is not used for heat here: it runs about 6 °F hot in summer against the stations.",
                    gloss = Gloss.Frost, moreOnly = true,
                )
            } ?: Answer("How many hot days and frost nights?", "", gloss = Gloss.Frost, moreOnly = true, ready = !loading && daily != null))
        }
        return FieldNowView(glance, answers)
    }

    /** What happened on this field in the last 3 seasons, one line each. */
    data class SeasonLine(val year: Int, val text: String, val strip: String)
    fun lastSeasons(loc: LocationDto, cal: FieldCalendar): List<SeasonLine> {
        val last = Timeline.yearOf(Calendars.lastDataT(cal)); val hist = FieldNames.history(loc)
        return cal.years.filter { it.year <= last && it.year > last - 3 }.reversed().map { y ->
            fun n(c: Char) = y.rule.count { it == c } * 10
            SeasonLine(y.year, "${FieldNames.cropName(hist[y.year])}. Green about ${n('c')} days, thin ${n('p')}, bare ${n('b')}, flooded ${n('w')}${if (n('u') > 0) ", no clear view ${n('u')}" else ""}.", y.rule)
        }
    }

    /** About the ground (shared.tsx AboutField), label to value. */
    fun aboutField(loc: LocationDto, cal: FieldCalendar?, insurance: InsuranceSummary?): List<Pair<String, String>> = buildList {
        val s = loc.soil
        val mu = s?.muname?.takeIf { known(it) && !it.contains("not fetched", true) }?.substringBefore(",").orEmpty()
        val tex = s?.textureClass?.takeIf(::known).orEmpty()
        if (mu.isNotEmpty() || tex.isNotEmpty()) add("Soil" to listOf(mu, tex.lowercase()).filter(String::isNotEmpty).joinToString(", "))
        s?.awcMmPerM?.value?.let { awc -> val inFt = awc / 1000 * 12; add("Holds" to "${Fmt.one(inFt)} in of water per foot of soil${if (inFt < 1.4) " (low: needs frequent, short irrigations)" else if (inFt > 2) " (high)" else ""}") }
        val dc = s?.drainageClass?.takeIf(::known).orEmpty(); val hg = s?.hydrologicGroup?.takeIf(::known).orEmpty()
        if (dc.isNotEmpty() || hg.isNotEmpty()) add("Drainage" to (dc + if (hg.isNotEmpty()) "${if (dc.isNotEmpty()) "; " else ""}runoff group $hg" else ""))
        s?.ecDsPerM?.let { add("Salt" to "${if (it >= 4) "Salty soil; limits salt-sensitive crops" else "Low salt"} (EC ${Fmt.one(it)} dS/m)") }
        val w = loc.water
        val src = when (w?.source) { "surface" -> "Surface water"; "groundwater" -> "Groundwater (wells)"; "mixed" -> "Surface water and wells"; else -> null }
        val real = w != null && (w.lookup == true || (w.district != null && !w.district.contains("(U)"))) && w.verified != false
        add("Water" to if (!real) listOfNotNull(src, "water district not looked up yet").joinToString("; ") else
            listOfNotNull(src, w!!.district).joinToString(". ") + "." + (w.sgmaStatus?.text?.let { " $it." } ?: ""))
        loc.terrain?.slopeMeanPct?.value?.let { sl ->
            add("Slope" to "${if (sl < 2) "Nearly flat" else if (sl < 5) "Gentle slope" else "Sloping"}, about ${Fmt.one(sl)}% on average${loc.terrain.lowSpotFraction?.value?.takeIf { it > 0 }?.let { "; low spots on about ${(it * 100).roundToInt()}% of the field, where water ponds and frost settles" } ?: ""}. NASA NASADEM elevation, 100 ft squares; radar elevation reads 1 to 2% on a levelled field.")
        }
        insurance?.let { r ->
            add("Crop insurance" to "${Fmt.usd(r.total)} paid out on ${r.scope} ${r.crop.replace("_forage", "").replace('_', ' ')}, ${r.from}–${r.to}; ${Fmt.usd(r.topUsd)} in ${r.topYear} alone.${if (r.shareDrought >= 0.3) " ${(r.shareDrought * 100).roundToInt()}% of it for drought or failed irrigation water." else ""} USDA Risk Management Agency, county totals, not this farm.")
        }
        val ob = SeasonCalc.observedBare(cal)
        add("Usually bare" to (ob?.let { "About ${it.value} days a year, mostly ${SeasonCalc.usuallyBareMonths(cal)}. Seen by satellite, ${it.years.first()}–${it.years.last()}. ${SeasonCalc.BARE_DEF}" } ?: "Not seen clearly enough yet"))
    }
}

data class InsuranceSummary(val scope: String, val crop: String, val total: Double, val from: Int, val to: Int, val topYear: Int, val topUsd: Double, val shareDrought: Double)

fun app.croplytics.data.remote.dto.InsuranceDto.summary(): InsuranceSummary? {
    val p = profiles.values.firstOrNull() ?: return null
    val total = p.totalIndemnityUsd ?: return null
    val ys = p.byYear.keys.mapNotNull { it.toIntOrNull() }
    val top = p.byYear.maxByOrNull { it.value } ?: return null
    return InsuranceSummary(p.scope.orEmpty(), p.crop.orEmpty(), total, ys.minOrNull() ?: 0, ys.maxOrNull() ?: 0, top.key.toInt(), top.value, p.shares["share_drought"]?.value ?: 0.0)
}
