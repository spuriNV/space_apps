package app.croplytics.domain

import app.croplytics.testing.Fixtures
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class FieldNamesTest {
    @Test
    fun `crop data layer labels become grower words`() {
        assertEquals("Left fallow", FieldNames.cropName("Fallow/Idle Cropland"))
        assertEquals("Wheat, then corn", FieldNames.cropName("Dbl Crop WinWht/Corn"))
        assertEquals("Oats, then Corn", FieldNames.cropName("Dbl Crop Oats/Corn"))
        assertEquals("Rice", FieldNames.cropName("Rice (CDL pending)"))
        assertEquals("Not recorded", FieldNames.cropName(null))
    }

    @Test
    fun `a field is named by its crop and the nearest town`() {
        val id = FieldNames.identity(Fixtures.location)
        assertEquals("Rice field 3.5 miles east of Williams", id.name)
        assertEquals(149, id.acres)
        assertEquals("Colusa", id.county)
        assertEquals("149 acres, rice in 2025, Colusa County", id.subtitle)
        assertEquals("Rice in 7 of the last 10 years; left fallow 2016, 2020 and 2022.", id.recordLine)
    }

    @Test
    fun `the API's farmer name and county win when present`() {
        val loc = Fixtures.json.decodeFromString(
            app.croplytics.data.remote.dto.LocationDto.serializer(),
            """{"id":"car_glenn_rice","farmer_name":"Rice field 3 miles southwest of Glenn","county":{"fips":"06021","name":"Glenn"},"acres":200.6,"centroid":{"lon":-122.05,"lat":39.49},"crop_history":{"2025":"Rice"}}""",
        )
        val id = FieldNames.identity(loc)
        assertEquals("Rice field 3 miles southwest of Glenn", id.name)
        assertEquals("Glenn", id.county)
        assertEquals(201, id.acres)
    }

    @Test
    fun `no town nearby gives no distance`() {
        assertNull(FieldNames.nearTown(45.0, -100.0))
        assertTrue(FieldNames.nearTown(36.20, -119.60)!!.matches(Regex("[0-9.]+ miles? [a-z]+ of [A-Za-z ]+")))
    }

    @Test
    fun `search text covers name, county and crop`() {
        val id = FieldNames.identity(Fixtures.location)
        assertTrue("colusa" in id.searchText && "rice" in id.searchText && "williams" in id.searchText)
    }
}
