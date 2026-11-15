package app.croplytics.data

import app.croplytics.data.remote.dto.LocationsDto
import app.croplytics.domain.FieldNames
import app.croplytics.testing.Fixtures
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** The list as the live API serves it now: 11 fields including the British Columbia one. */
class LiveShapesTest {
    @Test
    fun `the live field list parses, BC field included`() {
        val l = Fixtures.json.decodeFromString(LocationsDto.serializer(), Fixtures.text("locations_live.json"))
        assertEquals(11, l.items.size)
        val bc = l.items.first { it.region == "bc" }
        val id = FieldNames.identity(bc)
        assertEquals("Columbia-Shuswap, BC", id.place)
        assertTrue(id.name.startsWith("Hay field"))
    }
}
