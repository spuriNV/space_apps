package app.croplytics.ui

import android.app.Application
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performScrollToNode
import androidx.compose.ui.test.performTextInput
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.Modifier
import androidx.test.ext.junit.runners.AndroidJUnit4
import app.croplytics.data.repository.CalendarBundle
import app.croplytics.data.repository.LoadState
import app.croplytics.domain.FieldNames
import app.croplytics.testing.Fixtures
import app.croplytics.ui.app.CompareUi
import app.croplytics.ui.app.FieldData
import app.croplytics.ui.app.FieldItem
import app.croplytics.ui.app.MainUiState
import app.croplytics.ui.app.fieldPicker
import app.croplytics.ui.panels.CompareActions
import app.croplytics.ui.panels.PanelActions
import app.croplytics.ui.panels.comparePanel
import app.croplytics.ui.theme.CropLyticsTheme
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.annotation.Config
import java.time.Instant

/** Compose UI tests on the JVM (Robolectric). The sheet's sections are LazyListScope builders, so no map or server is needed. */
@RunWith(AndroidJUnit4::class)
@Config(sdk = [35], application = Application::class)
class ScreensUiTest {
    @get:Rule val compose = createComposeRule()

    private val items = Fixtures.locations.items.map { FieldItem(it, FieldNames.identity(it), emptyList()) }
    private val ready = LoadState.Ready(items, Instant.parse("2026-11-14T20:00:00Z"))

    @Test
    fun pickListShowsFieldsChipsAndOpensAField() {
        var opened: String? = null; var query = ""; var family: String? = null
        compose.setContent {
            CropLyticsTheme(darkTheme = false) {
                LazyColumn { fieldPicker(MainUiState(fields = ready), { query = it }, { family = it }, {}, { opened = it }, {}, {}) }
            }
        }
        compose.onNodeWithText("Pick your field").assertIsDisplayed()
        compose.onNodeWithText("Rice field 3.5 miles east of Williams").assertIsDisplayed()
        compose.onNodeWithTag("pk-search").performTextInput("kings")
        assertEquals("kings", query)
        compose.onNodeWithTag("chip-rice").performClick()
        assertEquals("rice", family)
        compose.onNodeWithTag("row-car_colusa_rice").performClick()
        assertEquals("car_colusa_rice", opened)
    }

    @Test
    fun pickListExplainsTheSleepingServer() {
        compose.setContent { CropLyticsTheme { LazyColumn { fieldPicker(MainUiState(fields = LoadState.Waking), {}, {}, {}, {}, {}, {}) } } }
        compose.onNodeWithText("Waking the server, up to a minute").assertIsDisplayed()
    }

    @Test
    fun compareShowsGainAndGiveUpAndSeeAllOptions() {
        val item = items.first { it.id.id == "car_colusa_rice" }
        val data = FieldData(item, calendar = LoadState.Ready(CalendarBundle(Fixtures.calendar, null), Instant.EPOCH), strategies = LoadState.Ready(Fixtures.scored3.items, Instant.EPOCH),
            limit = 3.0, exampleLimit = true)
        var table = 0; var brief: String? = null
        val a = PanelActions({}, {}, {}, {}, {}, {}, {})
        compose.setContent {
            CropLyticsTheme {
                LazyColumn(Modifier.testTag("list")) {
                    comparePanel(MainUiState(fields = ready, selectedId = "car_colusa_rice"), data, CompareUi(), emptyMap(), a,
                        CompareActions({}, { table++ }, {}, {}, {}, { _, _ -> }, {}, {}, { brief = it }))
                }
            }
        }
        compose.onNodeWithText("Dry-year safflower vs rice today").assertIsDisplayed()
        compose.onNodeWithText("example, change to yours").assertIsDisplayed()
        compose.onNodeWithTag("see-all").performScrollTo().performClick()
        assertEquals(1, table)
        compose.onNodeWithTag("list").performScrollToNode(hasTestTag("cmp-gain-list"))
        compose.onNodeWithText("You gain").assertExists()
        compose.onNodeWithTag("list").performScrollToNode(hasTestTag("to-brief"))
        compose.onNodeWithTag("to-brief").performClick()
        assertTrue(brief == "car2_dryyear_safflower")
    }
}
