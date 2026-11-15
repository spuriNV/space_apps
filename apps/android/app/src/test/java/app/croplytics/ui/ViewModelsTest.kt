package app.croplytics.ui

import androidx.lifecycle.SavedStateHandle
import app.croplytics.data.repository.LoadError
import app.croplytics.data.repository.LoadState
import app.croplytics.testing.FakeFieldRepository
import app.croplytics.testing.Fixtures
import app.croplytics.testing.MainDispatcherRule
import app.croplytics.ui.compare.CompareViewModel
import app.croplytics.ui.fields.FieldsViewModel
import app.croplytics.ui.now.FieldNowViewModel
import app.croplytics.ui.season.ComingSeasonViewModel
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import java.time.Clock
import java.time.Instant
import java.time.ZoneOffset

@OptIn(ExperimentalCoroutinesApi::class)
class ViewModelsTest {
    @get:Rule val main = MainDispatcherRule()

    private val repo = FakeFieldRepository()
    private val id = "car_colusa_rice"
    private val handle get() = SavedStateHandle(mapOf("id" to id))
    private val clock = Clock.fixed(Instant.parse("2026-11-14T20:00:00Z"), ZoneOffset.UTC)

    // ---- Fields ----

    @Test
    fun `fields list shows waking, then rows, and search narrows them`() = runTest {
        val vm = FieldsViewModel(repo)
        backgroundScope.launch { vm.state.collect {} }
        repo.locations.value = LoadState.Waking
        advanceUntilIdle()
        assertTrue(vm.state.value.waking)

        repo.locations.value = repo.ready(Fixtures.locations.items)
        advanceUntilIdle()
        assertEquals(2, vm.state.value.rows.size)
        assertEquals(2, vm.state.value.totalFields)

        vm.onQueryChange("kings alfalfa")
        advanceUntilIdle()
        assertEquals(listOf("caf_tulare_forage"), vm.state.value.rows.map { it.identity.id })

        vm.onQueryChange("almonds")
        advanceUntilIdle()
        assertTrue(vm.state.value.rows.isEmpty())
    }

    @Test
    fun `fields list says when it is showing the copy saved on the phone`() = runTest {
        val vm = FieldsViewModel(repo)
        backgroundScope.launch { vm.state.collect {} }
        repo.locations.value = LoadState.Ready(Fixtures.locations.items, repo.savedAt, offline = true)
        advanceUntilIdle()
        assertEquals(repo.savedAt, vm.state.value.offlineSavedAt)
    }

    @Test
    fun `retry asks the server again`() = runTest {
        val vm = FieldsViewModel(repo)
        backgroundScope.launch { vm.state.collect {} }
        repo.locations.value = LoadState.Failed(LoadError.NoConnection)
        advanceUntilIdle()
        assertEquals(LoadError.NoConnection, vm.state.value.error)
        vm.retry()
        advanceUntilIdle()
        assertEquals(1, repo.forcedReloads)
    }

    // ---- Field now ----

    @Test
    fun `field now builds the summary as parts arrive`() = runTest {
        val vm = FieldNowViewModel(handle, repo, clock)
        backgroundScope.launch { vm.state.collect {} }
        repo.location.value = repo.ready(Fixtures.location)
        advanceUntilIdle()
        assertEquals("Rice field 3.5 miles east of Williams", vm.state.value.identity!!.name)
        assertTrue(vm.state.value.partsLoading)

        repo.calendar.value = repo.ready(Fixtures.calendar)
        repo.nasaNow.value = repo.ready(Fixtures.nasaNow)
        repo.strategies.value = repo.ready(Fixtures.strategies.items)
        advanceUntilIdle()
        val s = vm.state.value
        assertFalse(s.partsLoading)
        assertEquals(4, s.summary!!.answers.size)
        // the example limit (5.0 for Colusa rice) is used until the grower sets one
        assertEquals("limit 5.0 (example)", s.summary!!.waterNeed!!.note)
        // routes the live server does not have yet show as "not available", never crash
        assertTrue(s.detail.stress is app.croplytics.ui.common.DetailPart.Unavailable)
    }

    @Test
    fun `field now uses the grower's saved limit`() = runTest {
        repo.limits.value = mapOf(id to 6.0)
        val vm = FieldNowViewModel(handle, repo, clock)
        backgroundScope.launch { vm.state.collect {} }
        repo.location.value = repo.ready(Fixtures.location)
        repo.strategies.value = repo.ready(Fixtures.strategies.items)
        advanceUntilIdle()
        assertEquals("limit 6.0", vm.state.value.summary!!.waterNeed!!.note)
    }

    @Test
    fun `field now shows the error when the field cannot load`() = runTest {
        val vm = FieldNowViewModel(handle, repo, clock)
        backgroundScope.launch { vm.state.collect {} }
        repo.location.value = LoadState.Failed(LoadError.Server)
        advanceUntilIdle()
        assertEquals(LoadError.Server, vm.state.value.error)
        assertFalse(vm.state.value.loading)
    }

    // ---- Coming season ----

    @Test
    fun `coming season gives three items`() = runTest {
        val vm = ComingSeasonViewModel(handle, repo)
        backgroundScope.launch { vm.state.collect {} }
        repo.location.value = repo.ready(Fixtures.location)
        repo.outlook.value = repo.ready(Fixtures.outlook)
        advanceUntilIdle()
        assertEquals(3, vm.state.value.summary!!.items.size)
    }

    // ---- Compare ----

    @Test
    fun `changing the water limit saves it for the field and re-scores`() = runTest {
        repo.scoreResult = { repo.ready(Fixtures.scored3.items) }
        repo.location.value = repo.ready(Fixtures.location)
        repo.strategies.value = repo.ready(Fixtures.strategies.items)
        val vm = CompareViewModel(handle, repo)
        backgroundScope.launch { vm.state.collect {} }
        advanceUntilIdle()
        assertEquals(5.0, vm.state.value.limit!!, 1e-9)
        assertTrue(vm.state.value.limitIsExample)
        assertEquals(listOf(5.0), repo.scoreRequests)

        vm.onLimitChange(3.04)
        advanceTimeBy(100)
        assertEquals(3.0, vm.state.value.limit!!, 1e-9) // rounded to 0.1, shown at once
        advanceUntilIdle()
        assertEquals(mapOf(id to 3.0), repo.limits.value) // saved per field
        assertEquals(listOf(5.0, 3.0), repo.scoreRequests) // one re-score after the slider settles
        val s = vm.state.value
        assertFalse(s.limitIsExample)
        assertFalse(s.rescoring)
        assertEquals("car2_dryyear_safflower", s.summary!!.top.first().id)
        assertEquals(2, s.summary!!.top.size)
    }

    @Test
    fun `a failed re-score falls back to the server's default ranking`() = runTest {
        repo.scoreResult = { LoadState.Failed(LoadError.Server) }
        repo.location.value = repo.ready(Fixtures.location)
        repo.strategies.value = repo.ready(Fixtures.strategies.items)
        val vm = CompareViewModel(handle, repo)
        backgroundScope.launch { vm.state.collect {} }
        advanceUntilIdle()
        assertTrue(vm.state.value.rescoreFailed)
        assertNotNull(vm.state.value.summary)
    }

    @Test
    fun `see all options toggles the full list`() = runTest {
        repo.location.value = repo.ready(Fixtures.location)
        repo.strategies.value = repo.ready(Fixtures.strategies.items)
        val vm = CompareViewModel(handle, repo)
        backgroundScope.launch { vm.state.collect {} }
        advanceUntilIdle()
        assertFalse(vm.state.value.showAll)
        vm.toggleShowAll()
        advanceUntilIdle()
        assertTrue(vm.state.value.showAll)
    }
}
