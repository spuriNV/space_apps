package app.croplytics.domain

import app.croplytics.testing.Fixtures
import app.croplytics.ui.app.FieldItem
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class StackBorrowTest {
    private val loc = Fixtures.locations.items.first { it.id == "car_colusa_rice" }
    private val loc2 = Fixtures.locations.items.first { it.id == "caf_tulare_forage" }
    private val item = FieldItem(loc, FieldNames.identity(loc), loc.geometry!!.rings())
    private val item2 = FieldItem(loc2, FieldNames.identity(loc2), loc2.geometry!!.rings())

    @Test
    fun `shifts a borrowed grid onto the target field`() {
        val shifted = StackBorrow.shiftGrid(Fixtures.grid, item2, item)
        val dLon = item.id.lon - item2.id.lon
        val orig = Fixtures.grid.cells.first().ring
        val out = shifted.cells.first().ring
        assertTrue(out[0] == orig[0] + dLon)
    }

    @Test
    fun `uses nearest preset grid while the field grid is still loading`() {
        val fields = listOf(item, item2)
        val borrow = StackBorrow.nearest(item, fields)
        assertNotNull(borrow)
        val inputs = StackBorrow.inputs(item, fields, null, Fixtures.calendar, Fixtures.regional, borrow, Fixtures.grid, null, null)
        assertNotNull(inputs)
        assertTrue(Map3D.stack(item.rings, item.id.lat, 60.0, inputs!!.grid, Map3D.offsets(inputs.grid), inputs.calendar, inputs.regional, Timeline.todayT(Fixtures.today), MapDatasets.DEFAULT_ON) != null)
    }
}