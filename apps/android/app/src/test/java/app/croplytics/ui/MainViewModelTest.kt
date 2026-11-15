package app.croplytics.ui

import app.croplytics.data.repository.CalendarBundle
import app.croplytics.data.repository.LoadState
import app.croplytics.domain.CompareLogic
import app.croplytics.domain.Timeline
import app.croplytics.testing.FakeFieldRepository
import app.croplytics.testing.Fixtures
import app.croplytics.testing.MainDispatcherRule
import app.croplytics.ui.app.MainViewModel
import app.croplytics.ui.app.MapCommand
import app.croplytics.ui.app.Tab
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import java.time.Clock
import java.time.Instant
import java.time.ZoneOffset

@OptIn(ExperimentalCoroutinesApi::class)
class MainViewModelTest {
    @get:Rule val main = MainDispatcherRule()

    private val repo = FakeFieldRepository()
    private val clock = Clock.fixed(Instant.parse("2026-11-14T20:00:00Z"), ZoneOffset.UTC)
    private val id = "car_colusa_rice"

    private fun vm() = MainViewModel(repo, clock)

    @Test
    fun `the pick list filters by crop family and words`() = runTest {
        val vm = vm()
        backgroundScope.launch { vm.state.collect {} }
        repo.locations.value = repo.ready(Fixtures.locations.items)
        advanceUntilIdle()
        assertEquals(listOf("rice" to 1, "forage" to 1), vm.state.value.families)
        vm.toggleFamily("forage"); advanceUntilIdle()
        assertEquals(listOf("caf_tulare_forage"), vm.state.value.shown.map { it.id.id })
        vm.toggleFamily("forage"); vm.onQuery("williams rice"); advanceUntilIdle()
        assertEquals(listOf(id), vm.state.value.shown.map { it.id.id })
        assertEquals(mapOf(2026 to "c".repeat(36)), vm.state.value.strips[id])
    }

    @Test
    fun `picking a field flies the map to it and loads its data with the example limit`() = runTest {
        val vm = vm()
        val cmds = mutableListOf<MapCommand>()
        backgroundScope.launch { vm.mapCommands.collect { cmds += it } }
        backgroundScope.launch { vm.field.collect {} }
        repo.locations.value = repo.ready(Fixtures.locations.items)
        repo.calendar.value = repo.ready(CalendarBundle(Fixtures.calendar, null))
        repo.strategies.value = repo.ready(Fixtures.strategies.items)
        repo.scoreResult = { repo.ready(Fixtures.scored3.items) }
        advanceUntilIdle()
        vm.select(id); advanceUntilIdle()
        val fly = cmds.last() as MapCommand.FlyToField
        assertEquals(MapCommand.FlyToField.Mode.Card, fly.mode)
        assertEquals(39.14, fly.lat, 0.01) // the command carries the field's centre
        val f = vm.field.value!!
        assertEquals(id, f.item.id.id)
        assertEquals(5.0, f.limit!!, 1e-9)
        assertTrue(f.exampleLimit)
        // GET /strategies re-scored for the limit, OpenET check kept from GET
        assertEquals(5.0, repo.scoreRequests.last().first, 1e-9)
        assertTrue((f.strategies as LoadState.Ready).data.first { it.isBaseline }.water.etcVsOpenetPct?.usable != null)
    }

    @Test
    fun `the viewing date never goes past today and replay steps forward`() = runTest {
        val vm = vm()
        backgroundScope.launch { vm.state.collect {} }
        assertEquals(Timeline.tOf(2026, 31), vm.todayT)
        vm.setT(vm.todayT + 10); advanceUntilIdle()
        assertEquals(vm.todayT, vm.state.value.t)
        val floods = vm.quickDates.first { it.label == "2023 floods" }
        vm.setT(floods.t); advanceUntilIdle()
        assertFalse(vm.state.value.isToday)
        vm.togglePlay(); advanceTimeBy(700)
        assertTrue(vm.state.value.t > floods.t)
        vm.togglePlay(); vm.backToToday(); advanceUntilIdle()
        assertTrue(vm.state.value.isToday)
        assertFalse(vm.state.value.playing)
    }

    @Test
    fun `tabs need a field, and home returns to the pick list`() = runTest {
        val vm = vm()
        backgroundScope.launch { vm.state.collect {} }
        repo.locations.value = repo.ready(Fixtures.locations.items); advanceUntilIdle()
        vm.openTab(Tab.Compare); advanceUntilIdle()
        assertEquals(Tab.Now, vm.state.value.tab)
        vm.select(id); vm.openTab(Tab.Compare); advanceUntilIdle()
        assertEquals(Tab.Compare, vm.state.value.tab)
        vm.goHome(); advanceUntilIdle()
        assertNull(vm.state.value.selectedId)
    }

    @Test
    fun `priorities and what-ifs re-score once the grower stops tapping`() = runTest {
        val vm = vm()
        backgroundScope.launch { vm.compare.collect {} }
        backgroundScope.launch { vm.field.collect {} }
        repo.locations.value = repo.ready(Fixtures.locations.items)
        repo.strategies.value = repo.ready(Fixtures.strategies.items)
        repo.scoreResult = { repo.ready(Fixtures.scored3.items) }
        advanceUntilIdle(); vm.select(id); advanceUntilIdle()
        val before = repo.scoreRequests.size
        vm.compareWeight("water_use", 4); vm.compareRain(-20.0); advanceTimeBy(100)
        assertTrue(vm.compare.value.busy)
        advanceUntilIdle()
        val req = repo.scoreRequests.drop(before).last()
        assertEquals(4.0, req.second!!["water_use"]); assertEquals(-20.0, req.third!!.dPPct, 0.0)
        assertTrue(vm.compare.value.custom)
        assertEquals(4, vm.compare.value.rescored!!.size)
        vm.compareWeather(CompareLogic.Weather.Dry); advanceUntilIdle()
        assertEquals(CompareLogic.Weather.Dry, vm.compare.value.weather)
    }

    @Test
    fun `the water limit is saved per field`() = runTest {
        val vm = vm()
        backgroundScope.launch { vm.state.collect {} }
        repo.locations.value = repo.ready(Fixtures.locations.items); advanceUntilIdle()
        vm.select(id); vm.setLimit(3.04); advanceUntilIdle()
        assertEquals(mapOf(id to 3.0), repo.limits.value)
    }

    @Test
    fun `a deep link opens the field section once the fields are in`() = runTest {
        val vm = vm()
        backgroundScope.launch { vm.state.collect {} }
        vm.deepLink(id, Tab.Year.ordinal)
        repo.locations.value = repo.ready(Fixtures.locations.items); advanceUntilIdle()
        assertEquals(id, vm.state.value.selectedId)
        assertEquals(Tab.Year, vm.state.value.tab)
    }
}
