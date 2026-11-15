package app.croplytics.domain

import app.croplytics.data.remote.dto.FirstNationsDto
import app.croplytics.data.remote.dto.InsuranceDto
import app.croplytics.data.remote.dto.LocationDto
import app.croplytics.data.remote.dto.StrategyCalendarDto
import app.croplytics.data.remote.dto.StrategyDto
import app.croplytics.testing.Fixtures
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** The British Columbia field: watershed and orders, gap lines, estimates, First Nations, rain-fed rotations. */
class BcTest {
    private val bc: LocationDto = Fixtures.json.decodeFromString(LocationDto.serializer(), Fixtures.text("location_bc.json"))

    @Test
    fun `the BC field reads as BC everywhere`() {
        assertTrue(bc.isBC)
        assertEquals("AAFC Annual Crop Inventory (Agriculture Canada)", BcLogic.cropMapName(bc))
        assertTrue(BcLogic.stationsName(bc).startsWith("Environment Canada"))
        val about = FieldNowLogic.aboutField(bc, null, null, Fixtures.json.decodeFromString(InsuranceDto.serializer(), Fixtures.text("insurance_bc.json")))
        val shed = about.first { it.first == "Watershed" }.second
        assertTrue(shed.startsWith("Salmon River (Shuswap), lower reach."))
        assertTrue(shed.contains("order to stop irrigating forage") && shed.contains("order rescinded"))
        assertTrue(about.first { it.first == "Crop losses" }.second.startsWith("Usual causes of crop loss here: drought"))
    }

    @Test
    fun `gap lines say not available in BC, or what fills the gap`() {
        val g = bc.gap("openet")!!
        assertTrue(BcLogic.gapLine(g, missing = true)!!.startsWith("Not available in BC. OpenET covers the western United States only"))
        assertTrue(BcLogic.gapLine(g, missing = false)!!.contains("Estimated from the rotation engine"))
        assertNull(Fixtures.location.gap("openet")) // California fields have no gaps
    }

    @Test
    fun `rain-fed rotations never read as zero acre-feet`() {
        val rf = StrategyDto("bc3_sainfoin_grass", "Dryland sainfoin-meadow brome hay", calendar = listOf(StrategyCalendarDto(1, "sainfoin", irrigated = false)))
        assertTrue(BcLogic.rainFed(rf))
        assertFalse(BcLogic.rainFed(Fixtures.strategies.items.first()))
        assertEquals("Rain-fed (no irrigation)", CompareLogic.needText(rf, CompareLogic.Weather.Typical))
        assertEquals("Fits your limit", CompareLogic.fits(rf, CompareLogic.Weather.Typical, 0.5))
    }

    @Test
    fun `the First Nations card parses with reserves, steps and principles`() {
        val fn = Fixtures.json.decodeFromString(FirstNationsDto.serializer(), Fixtures.text("first_nations_bc.json"))
        assertFalse(fn.fieldOnReserve)
        assertEquals("Splatsin", fn.lowerRiverNation!!.nation)
        assertTrue(fn.nearby.isNotEmpty() && fn.engagementSteps.isNotEmpty() && fn.principles.isNotEmpty())
        assertEquals("Salmon River 1 (Splatsin)", BcLogic.reserveName("SALMON RIVER 1 (SPLATSIN)"))
    }

    @Test
    fun `an estimated machine-learning calendar says so`() {
        val v = YearLogic.mlVerdict(MLInfo(null, null, false, false, 12.0, "rule", estimate = true))
        assertEquals("An estimate, not a trained model", v.short)
    }
}
