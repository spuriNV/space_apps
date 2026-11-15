package app.croplytics.domain

import app.croplytics.data.remote.dto.LocationDto
import app.croplytics.testing.Fixtures
import kotlinx.serialization.json.JsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** The 1.3.0 decoders, on payloads trimmed from the live API (15 Nov 2026). */
class ExtrasTest {
    private fun obj(name: String) = Fixtures.json.decodeFromString(JsonObject.serializer(), Fixtures.text(name))

    @Test
    fun `this week for an irrigated forage field has a need strip, access chips and a forecast in inches and F`() {
        val w = WeekLogic.parse(obj("this_week_irrigate.json"))
        assertEquals("irrigate", w.kind)
        assertEquals("Irrigate about 0.2 in this week", w.verdict)
        assertEquals(0.241, w.acreInPerAcre!!, 1e-6)
        assertEquals(4, w.need.size)
        assertEquals("Sun", w.need.first().dow)
        assertEquals(1.924 / 25.4, w.need.first().needIn, 1e-6)
        assertEquals(listOf("ok", "too_wet", "too_wet", "ok"), w.access.map { it.status })
        assertEquals(listOf("OK", "Wet", "Wet", "OK"), w.access.map { it.word })
        assertEquals("Too wet Mon–Tue after rain", w.accessLine)
        assertTrue(w.access[1].why.isNotBlank())
        val d = w.forecast.first()
        assertEquals("Sun", d.dow)
        assertEquals(0.0, d.rainIn!!, 1e-9)
        assertEquals(69, d.hiF) // 20.5 C
        assertEquals(43, d.loF) // 6.0 C
        assertTrue(w.alerts.isEmpty())
    }

    @Test
    fun `a flooded field shows the verdict but no need strip`() {
        val w = WeekLogic.parse(obj("this_week_flooded.json"))
        assertEquals("Flooded paddy: keep water at depth", w.verdict)
        assertTrue(w.need.isEmpty())
        assertEquals("Too wet to work until Sat", w.accessLine)
        assertEquals(4, w.forecast.size)
        assertEquals("0.5", WeekLogic.inches(12.9)) // 12.9 mm
        assertEquals(57, w.forecast.first().hiF) // 13.8 C
    }

    @Test
    fun `sections that are unavailable are hidden`() {
        val j = obj("this_week_irrigate.json")
        val sec = kotlinx.serialization.json.buildJsonObject {
            put("forecast", kotlinx.serialization.json.buildJsonObject { put("status", kotlinx.serialization.json.JsonPrimitive("unavailable")) })
            put("alerts", kotlinx.serialization.json.buildJsonObject { put("status", kotlinx.serialization.json.JsonPrimitive("ready")) })
            put("irrigation", kotlinx.serialization.json.buildJsonObject { put("status", kotlinx.serialization.json.JsonPrimitive("fallback")) })
            put("field_access", kotlinx.serialization.json.buildJsonObject { put("status", kotlinx.serialization.json.JsonPrimitive("not_applicable")) })
        }
        val w = WeekLogic.parse(JsonObject(j + ("sections" to sec)))
        assertTrue(w.forecast.isEmpty()); assertTrue(w.access.isEmpty())
        assertEquals("From a backup forecast.", w.irrigationTag)
        assertTrue(w.verdict.isNotBlank())
    }

    @Test
    fun `the catalog parses pins and crop groups`() {
        val c = CatalogLogic.parse(obj("catalog_live.json"))
        assertEquals(6, c.pins.size)
        val p = c.pins.first()
        assertEquals("pt_n503464_w1192638", p.id)
        assertEquals(50.3464, p.lat, 1e-9); assertEquals(-119.2638, p.lon, 1e-9)
        assertEquals("orchard", p.group)
        assertEquals(16, c.groups.size)
        assertEquals("grain", c.groups.first().key) // sorted by count
        assertEquals("#0072B2", CatalogLogic.color("rice"))
        assertEquals("R", CatalogLogic.letter("rice"))
    }

    @Test
    fun `a tapped spot answers as a location with a pt id and a grower name`() {
        val loc = Fixtures.json.decodeFromString(LocationDto.serializer(), Fixtures.text("analyze_live.json"))
        assertEquals("pt_n363000_w1196000", loc.id)
        assertNotNull(loc.geometry)
        assertTrue(loc.geometry!!.rings().first().size >= 3)
        val id = FieldNames.identity(loc)
        assertEquals("Forage spot in Kings County, CA", id.name)
        assertEquals("forage", id.family)
        assertEquals(2025, id.latestCropYear)
    }

    @Test
    fun `drawn points make an area in acres`() {
        // about 0.002 deg square near Hanford: roughly 10 acres
        val sq = listOf(-119.60 to 36.30, -119.598 to 36.30, -119.598 to 36.302, -119.60 to 36.302)
        val a = DrawLogic.acres(sq)
        assertTrue("acres $a", a in 9.0..11.0)
        assertEquals(5, DrawLogic.closed(sq).size)
        assertEquals(0.0, DrawLogic.acres(sq.take(2)), 0.0)
    }
}
