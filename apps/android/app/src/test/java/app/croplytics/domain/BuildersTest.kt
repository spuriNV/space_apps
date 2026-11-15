package app.croplytics.domain

import app.croplytics.testing.Fixtures
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDate

class BuildersTest {
    private val today = LocalDate.of(2026, 11, 14)

    @Test
    fun `field now leads with a visual summary and at most four answers`() {
        val s = FieldNowBuilder.build(Fixtures.location, Fixtures.calendar, Fixtures.nasaNow, Fixtures.strategies.items, 5.0, true, today)
        assertEquals(4, s.answers.size)
        // rain: 48 mm of a 77 mm normal since 1 Oct (NASA IMERG)
        assertEquals("1.9 in", s.rain!!.value)
        assertEquals("62% of normal", s.rain!!.note)
        assertEquals("So far drier than normal", s.answers[1].headline)
        // water: today's rotation needs 5.2 acre-ft/acre against an example limit of 5.0
        assertEquals("5.2 acre-ft/acre", s.waterNeed!!.value)
        assertTrue(s.waterNeed!!.warn)
        assertEquals("Short by about 0.2 acre-feet per acre", s.answers[2].headline)
        assertTrue(s.answers[2].detail.contains("example limit"))
        // greenness from NASA HLS and the percentile track from GRACE-FO
        assertEquals("0.22", s.greenness!!.value)
        assertEquals(53, s.soil!!.groundwater)
        assertEquals(2026, s.strip!!.year)
        assertEquals(36, s.strip!!.steps.size)
        assertEquals(CoverCalendar.stepOf(today), s.strip!!.todayStep)
    }

    @Test
    fun `every number in field now carries its unit or meaning`() {
        val s = FieldNowBuilder.build(Fixtures.location, Fixtures.calendar, Fixtures.nasaNow, Fixtures.strategies.items, 6.0, false, today)
        s.answers.forEach { assertTrue("cite missing for ${it.question}", it.cite.isNotBlank()) }
        assertEquals("Fits your limit in a typical year", s.answers[2].headline)
        assertFalse(s.answers[2].detail.contains("example"))
    }

    @Test
    fun `field now without readings still answers what it can`() {
        val s = FieldNowBuilder.build(Fixtures.location, null, null, null, null, true, today)
        assertEquals(1, s.answers.size)
        assertEquals(null, s.rain)
    }

    @Test
    fun `coming season is exactly three items, outlooks not forecasts`() {
        val s = ComingSeasonBuilder.build(Fixtures.outlook, 5.0, true, CompareBuilder::shortName)
        assertEquals(3, s.items.size)
        assertEquals("NOAA's outlook leans wetter than normal this winter", s.items[0].headline)
        assertEquals("Reservoirs a little below average for the date", s.items[1].headline)
        assertTrue(s.items[1].detail.contains("Shasta 92% of average"))
        assertTrue(s.items[2].headline.startsWith("About 5.2 acre-feet per acre"))
        assertTrue(s.items[2].detail.contains("Dry-year safflower would need about 1.9"))
        assertTrue(s.lede.contains("not forecasts"))
        assertNotNull(s.bareWindow)
    }

    @Test
    fun `outlook season codes read as months`() {
        assertEquals("Nov–Jan", ComingSeasonBuilder.seasonMonths("NDJ"))
        assertEquals("Feb–Apr", ComingSeasonBuilder.seasonMonths("FMA"))
        assertEquals("Jun–Aug", ComingSeasonBuilder.seasonMonths("JJA"))
    }

    @Test
    fun `compare puts today against the two best options with gains and give-ups`() {
        val s = CompareBuilder.build(Fixtures.scored3.items, 3.0, 149)!!
        assertEquals("Rice + winter flood", s.today.name)
        assertEquals(LimitFit.Over, s.today.fit)
        assertEquals(listOf("car2_dryyear_safflower", "car1_rice_wintercover"), s.top.map { it.id })
        assertEquals(3, s.all.size)
        val safflower = s.top[0]
        assertEquals("Dry-year safflower", safflower.name)
        assertEquals("Needs less irrigation water", safflower.gains.first().title)
        assertTrue(safflower.gains.first().amount.startsWith("about 3.3 acre-ft/acre less a year"))
        assertTrue(safflower.gains.first().amount.contains("acre-feet across 149 acres"))
        assertTrue(safflower.giveUps.any { it.title == "Field bare more days" })
        assertTrue(s.openetLine.contains("16% high"))
    }

    @Test
    fun `limit fit uses the whole likely range`() {
        assertEquals(LimitFit.Fits, CompareBuilder.fit(Range(2.0, 1.5, 2.5), 3.0))
        assertEquals(LimitFit.MayGoOver, CompareBuilder.fit(Range(2.8, 2.4, 3.4), 3.0))
        assertEquals(LimitFit.Over, CompareBuilder.fit(Range(5.2, 4.1, 6.4), 3.0))
        assertEquals(LimitFit.Unknown, CompareBuilder.fit(null, 3.0))
    }

    @Test
    fun `adviser summary keeps NASA sources first and lists local checks`() {
        val id = FieldNames.identity(Fixtures.location)
        val compare = CompareBuilder.build(Fixtures.scored3.items, 3.0, id.acres)!!
        val s = AdviserSummaryBuilder.build(id, null, null, compare, compare.top.first(), Fixtures.scored3.items, 3.0, true, today)
        assertTrue(s.sources.first().startsWith("NASA"))
        assertTrue(s.checkLocally.isNotEmpty() && s.checkLocally.none { it.contains("(U)") || it.contains("spec B") })
        assertTrue(s.limitLine!!.contains("example"))
        assertEquals("14 Nov 2026", s.preparedOn)
    }

    @Test
    fun `thumbnail box keeps the field inside and the aspect ratio`() {
        val rings = Fixtures.location.geometry!!.rings()
        val box = Imagery.box(rings, 4.0 / 3.0)!!
        assertEquals(4.0 / 3.0, (box.maxX - box.minX) / (box.maxY - box.minY), 1e-6)
        rings.flatten().forEach { (lon, lat) ->
            val (fx, fy) = box.fraction(lon, lat)
            assertTrue(fx in 0f..1f && fy in 0f..1f)
        }
    }
}
