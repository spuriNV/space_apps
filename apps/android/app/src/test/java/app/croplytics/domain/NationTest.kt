package app.croplytics.domain

import app.croplytics.testing.Fixtures
import kotlinx.serialization.json.JsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class NationTest {
    private fun obj(name: String) = Fixtures.json.decodeFromString(JsonObject.serializer(), Fixtures.text(name))

    @Test fun headNamesLandStatusNationsAndFlagsUnconfirmedPlaceNames() {
        val h = NationLogic.head(obj("nation_bc.json"))!!
        assertEquals("Not on reserve or trust land", h.landStatus)
        assertEquals("Neskonlith", h.near.first().nation)
        assertEquals("Switsemalph Indian Reserve No. 3", h.near.first().area)
        assertTrue(h.places.first().notConfirmed)
    }

    @Test fun droughtGivesSharesAndScenarios() {
        val d = NationLogic.drought(obj("nation_drought_bc.json"))!!
        assertEquals("Aug 15", d.cutoffLabel)
        assertEquals("Alfalfa", d.rows.first().name)
        assertTrue(d.rows.first().baseline)
        assertTrue(d.scenarios.any { it.requested })
        assertEquals(45.2, d.scenarios.first().mineUnmet!!, 0.01)
    }

    @Test fun landUsesLatestYearWithGreenUpAndLinks() {
        val l = NationLogic.land(obj("nation_land_bc.json"))
        assertNotNull(l.greenup); assertNull(l.greenReason)
        assertEquals("0 within 6.2 mi", l.fire7)
        assertTrue(l.links.any { it.first.startsWith("Burn scars") })
    }

    @Test fun landWithoutPhenologyKeepsOneQuietReason() {
        val l = NationLogic.land(Fixtures.json.decodeFromString(JsonObject.serializer(), """{"ndvi_status":{"status":"not_computed","reason":"no field imagery yet"}}"""))
        assertNull(l.greenup); assertEquals("No field imagery yet.", l.greenReason)
    }

    @Test fun fundingListsPrograms() {
        val f = NationLogic.funding(obj("nation_funding_bc.json"))!!
        assertEquals("aafc_pathfinder", f.programs.first().id)
        assertEquals("Open", NationLogic.statusWord(f.programs.first().status))
    }

    @Test fun salmonTrimKeepsSummaryAndDecodes() {
        val v = NationLogic.salmon(NationLogic.trimSalmon(obj("salmon_bc.json")))!!
        assertTrue(v.lines.first().startsWith("In August 2026"))
        assertEquals("Aug 1 to Sep 30", v.window)
        assertNotNull(v.flowNow)
    }

    @Test fun groundwaterReads() {
        val g = NationLogic.groundwater(Fixtures.json.decodeFromString(JsonObject.serializer(), """{"subbasin_title":"Colusa Subbasin","sgma_priority":"High","gsas":[{"name":"Colusa GSA"}],"gw_pctl_weekly":[{"week_start":"2026-08-31","gw_pctl":52.7}],"pumping_need_af_by_rotation":[{"name":"Rice (current)","pumping_need_af":772.8}]}"""))!!
        assertEquals(52, g.latestPctl); assertEquals("Rice" to 772, g.pumping.first())
    }
}
