package app.croplytics.domain

import app.croplytics.testing.Fixtures
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** The Kotlin ports of the web app's logic (lib.ts, season.ts, bare.ts, nasa.ts, FieldNow, ComingSeason, YearSheet, ComparePanel, RotationBrief). */
class WebPortTest {
    private val todayT = Timeline.todayT(Fixtures.today)

    @Test
    fun `ten-day steps match the web clock`() {
        assertEquals(391, todayT) // (2026 - 2016) * 36 + mid November
        assertEquals("Mid Nov 2026", Timeline.label(todayT))
        assertEquals(Timeline.tOf(2023, 7), Timeline.dateToT("2023-03-14"))
        assertEquals("2026-11-20", Timeline.cutoffOf(todayT))
        assertEquals("2024-02-29", Timeline.cutoffOf(Timeline.tOf(2024, 5)))
    }

    @Test
    fun `the calendar becomes 36 classes a year with the machine-learning row beside it`() {
        val cal = Fixtures.calendar
        assertEquals(11, cal.years.size)
        assertTrue(cal.year(2026)!!.rule.length == 36 && cal.year(2026)!!.rule.any { it != 'u' })
        assertTrue(cal.year(2016)!!.rule.all { it == 'u' }) // trimmed fixture: not served = hatched, never guessed
        assertTrue(cal.hasMl)
        assertEquals(2026, Timeline.yearOf(Calendars.lastDataT(cal)))
    }

    @Test
    fun `field now shows five answers by default, soil composition included`() {
        val v = FieldNowLogic.build(Fixtures.location, Fixtures.calendar, Fixtures.regional, Fixtures.nasaNow, Fixtures.strategies.items, Fixtures.daily,
            null, null, null, 5.0, true, todayT, todayT, loading = false)
        val shown = v.answers.filter { !it.moreOnly }
        assertEquals(
            listOf("What is growing, and how far along?", "How much rain so far this season?", "Will the water limit cover irrigation?",
                "Is the soil wetter or drier than usual? And the groundwater?", "What is the soil like?"),
            shown.map { it.question },
        )
        assertEquals("So far drier than normal", shown[1].headline)
        assertEquals("1.9 in since 1 Oct. Normal: 3.0 in.", shown[1].detail)
        assertEquals("Short by about 0.2 acre-feet per acre", shown[2].headline)
        assertTrue(shown[2].detail.endsWith("Example, change it on Compare."))
        assertEquals("Clay loam", shown[4].headline)
        assertNotNull(shown[4].soilMix)
        assertEquals("1.9 in", v.glance.rain.value)
        assertEquals("Limit 5.0 (example)", v.glance.need.note)
        assertTrue(v.answers.count { it.moreOnly } >= 3) // green cover, water used, stress, hot days behind More detail
    }

    @Test
    fun `rain so far and heat days come from the daily record for past dates`() {
        val r = SeasonCalc.rainSoFar(Fixtures.daily, Timeline.tOf(2025, 6))!!
        assertTrue(r.period.label.startsWith("since 1 Oct 2024"))
        assertTrue(r.inches > 0)
        assertNotNull(SeasonCalc.heatFrost(Fixtures.daily, Timeline.tOf(2025, 20)))
    }

    @Test
    fun `compare keeps the web's verdict rules and month strips`() {
        val ss = Fixtures.scored3.items
        val today = ss.first { it.isBaseline }; val saff = ss.first { it.id == "car2_dryyear_safflower" }
        assertEquals(12, CompareLogic.monthStrip(saff).cover.length)
        assertEquals(CompareLogic.Verdict.Better, CompareLogic.verdict(Range(1.9, 1.5, 2.5), Range(5.2, 4.1, 6.4), hib = false))
        assertEquals(CompareLogic.Verdict.Unclear, CompareLogic.verdict(Range(5.1, 4.0, 6.2), Range(5.2, 4.1, 6.4), hib = false))
        val ctx = CompareLogic.ctx(ss, Fixtures.daily, Fixtures.calendar)
        val rows = CompareLogic.rows(saff, today, CompareLogic.Weather.Typical, ctx, ss, detail = false, heavySoil = true)
        assertEquals(CompareLogic.UNIT_METRICS.size, rows.size)
        assertEquals(CompareLogic.Verdict.Better, rows.first { it.m.key == "water" }.v)
        assertTrue(CompareLogic.delta(rows[0].m, 1.9, 5.2).startsWith("about 3.3 acre-ft/acre less a year"))
        assertEquals("Dry-year safflower", CompareLogic.shortName(saff))
        assertEquals("Fits your limit", CompareLogic.fits(saff, CompareLogic.Weather.Typical, 3.0))
        val w = CompareLogic.requestWeights(mapOf("water_use" to 4))
        assertEquals(4.0, w["water_use"]); assertEquals(0.0, w["market"]); assertEquals(0.0, w["pest_break"])
    }

    @Test
    fun `coming season leads with three short answers`() {
        val v = SeasonLogic.build(Fixtures.location, Fixtures.outlook, Fixtures.nasaNow, Fixtures.regional, Fixtures.strategies.items, Fixtures.calendar, Fixtures.daily, 5.0, true, todayT, false)
        assertEquals("Wetter than normal this winter", v.headline)
        assertEquals("Leans wetter than normal this winter.", v.winterRain)
        assertEquals("Shasta: 92% of average. Your allocation: 100%.", v.supply)
        assertEquals("Needs 5.2 acre-ft/acre. Limit 5.0 (example). 0.2 short.", v.nextNeed)
        assertEquals(4, v.outlookRows.size)
        assertTrue(v.bareTitle.startsWith("Usually bare from mid Feb"))
    }

    @Test
    fun `this field's year has a typical year and one strip per season`() {
        val v = YearLogic.build(Fixtures.location, Fixtures.calendar, Fixtures.daily, Parsers.ml(Fixtures.models, "random_forest", 17.8), null, null, todayT, showEarlier = false, detail = true)
        assertEquals(listOf(2026, 2025, 2024, 2023), v.rows.map { it.year })
        assertEquals(36, v.typical.length)
        assertEquals("Second opinion only", v.verdict.short) // 99% on a held-out year is too good to take at face value
        assertEquals("c", YearLogic.typical(listOf(CalYear(1, "", "c".repeat(36), "", List(36) { 0.0 }, null, null), CalYear(2, "", "b" + "c".repeat(35), "", List(36) { 0.0 }, null, null))).take(1))
    }

    @Test
    fun `the 3D stack rises from the 30 m grid with three labelled slabs`() {
        val loc = Fixtures.location
        val rings = loc.geometry!!.rings()
        val s = Map3D.stack(rings, loc.centroid.lat, loc.areaHa!!.value!!, Fixtures.grid, Map3D.offsets(Fixtures.grid), Fixtures.calendar, Fixtures.regional, todayT, MapDatasets.DEFAULT_ON)!!
        assertEquals(Fixtures.grid.cells.size, s.cells.size)
        assertEquals(listOf("hls", "smap", "grace"), s.labels.map { it.key })
        assertTrue(s.cells.all { it.height > it.base })
        assertEquals(4, s.posts.size)
        val fps = Map3D.footprints(rings, loc.centroid.lon, loc.centroid.lat, MapDatasets.DEFAULT_ON, smapLive = false)
        assertEquals(listOf("smap", "grace"), fps.map { it.id })
        assertTrue(fps.first().label.contains("6-mile square") && fps.first().label.endsWith("(still downloading)"))
        assertTrue(Map3D.pixelRatio(MapDatasets.ALL.first { it.id == "smap" }, 60.25).startsWith("1 pixel ≈"))
    }

    @Test
    fun `the NASA list puts what is live on screen first`() {
        val list = Nasa.list(Fixtures.location.nasaDatasets, Fixtures.location.datasets.mapValues { it.value.status }, mapOf("grace" to NasaStatus.Live, "hls" to NasaStatus.Live))
        assertEquals(11, list.size)
        assertEquals(NasaStatus.Live, list.first().status)
        assertTrue(list.indexOfFirst { it.status != NasaStatus.Live } > list.indexOfLast { it.status == NasaStatus.Live })
    }

    @Test
    fun `the adviser summary follows the printed page`() {
        val b = BriefLogic.build(Fixtures.location, Fixtures.scored3.items, "car2_dryyear_safflower", 3.0, true, Fixtures.outlook, Fixtures.nasaNow, Fixtures.calendar, Fixtures.daily, todayT, "14 Nov 2026")!!
        assertFalse(b.optionIsToday)
        assertEquals("Dry-year safflower", b.option)
        // with no pick the page opens on the first alternative, as the web does
        assertEquals("Rice + winter cover", BriefLogic.build(Fixtures.location, Fixtures.scored3.items, null, 3.0, true, null, null, null, null, todayT, "")!!.option)
        assertEquals("fits", b.table.first { it.pick }.against)
        assertTrue(b.gains!!.any { it.startsWith("Needs less irrigation water") })
        assertTrue(b.likely.first().startsWith("NOAA’s rain outlook"))
        assertTrue(b.checks.none { it.first.contains("(U)") || it.first.contains("spec B") })
        assertTrue(b.sources.startsWith("NASA:"))
    }

    @Test
    fun `NASA series feed the soil and groundwater percentiles`() {
        val r = Fixtures.regional
        assertEquals("grace_da", r.soilSource)
        assertNotNull(latestAt(r.groundwater, todayT))
    }
}
