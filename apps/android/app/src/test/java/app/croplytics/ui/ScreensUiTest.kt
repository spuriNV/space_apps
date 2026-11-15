package app.croplytics.ui

import android.app.Application
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollToNode
import androidx.compose.ui.test.performTextInput
import androidx.compose.ui.test.hasContentDescription
import androidx.compose.ui.test.hasTestTag
import androidx.test.ext.junit.runners.AndroidJUnit4
import app.croplytics.data.repository.LoadError
import app.croplytics.domain.CompareBuilder
import app.croplytics.domain.FieldNames
import app.croplytics.testing.Fixtures
import app.croplytics.ui.compare.CompareContent
import app.croplytics.ui.compare.CompareUiState
import app.croplytics.ui.fields.FieldRow
import app.croplytics.ui.fields.FieldsContent
import app.croplytics.ui.fields.FieldsUiState
import app.croplytics.ui.theme.CropLyticsTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.annotation.Config

/** Compose UI tests on the JVM (Robolectric). Stateless screens, so no server or Hilt is needed. */
@RunWith(AndroidJUnit4::class)
@Config(sdk = [35], application = Application::class)
class ScreensUiTest {
    @get:Rule val compose = createComposeRule()

    private val rows = Fixtures.locations.items.map { FieldRow(FieldNames.identity(it), emptyList()) }

    @Test
    fun fieldsListShowsFarmerNamesAndOpensAField() {
        var opened: String? = null
        var query = ""
        compose.setContent {
            CropLyticsTheme(darkTheme = false) {
                FieldsContent(FieldsUiState(rows = rows, totalFields = 2, loading = false), onQuery = { query = it }, onRetry = {}, onOpenField = { opened = it })
            }
        }
        compose.onNodeWithText("Pick your field").assertIsDisplayed()
        compose.onNodeWithText("Rice field 3.5 miles east of Williams").assertIsDisplayed()
        compose.onNodeWithText("149 acres, rice in 2025, Colusa County").assertIsDisplayed()
        compose.onNodeWithTag("field-search").performTextInput("kings")
        assertEquals("kings", query)
        compose.onNodeWithTag("field-row-car_colusa_rice").performClick()
        assertEquals("car_colusa_rice", opened)
    }

    @Test
    fun fieldsListExplainsTheSleepingServer() {
        compose.setContent {
            CropLyticsTheme { FieldsContent(FieldsUiState(waking = true), {}, {}, {}) }
        }
        compose.onNodeWithText("Waking the server, up to a minute").assertIsDisplayed()
    }

    @Test
    fun fieldsListErrorOffersTryAgain() {
        var retried = 0
        compose.setContent {
            CropLyticsTheme { FieldsContent(FieldsUiState(loading = false, error = LoadError.NoConnection), {}, { retried++ }, {}) }
        }
        compose.onNodeWithText("No connection").assertIsDisplayed()
        compose.onNodeWithText("Try again").performClick()
        assertEquals(1, retried)
    }

    @Test
    fun compareShowsTodayVsTopTwoAndEditsTheLimit() {
        val summary = CompareBuilder.build(Fixtures.scored3.items, 3.0, 149)!!
        var limit: Double? = null
        var toggled = 0
        compose.setContent {
            CropLyticsTheme {
                CompareContent(
                    CompareUiState(loading = false, limit = 3.0, limitIsExample = true, summary = summary),
                    onLimitChange = { limit = it }, onToggleAll = { toggled++ }, onRetry = {}, onSummary = {},
                )
            }
        }
        compose.onNodeWithText("3.0 acre-ft/acre").assertIsDisplayed()
        compose.onNodeWithText("example, change to yours").assertIsDisplayed()
        compose.onNode(hasContentDescription("Raise the limit by 0.1")).performClick()
        assertEquals(3.1, limit!!, 1e-9)
        compose.onNodeWithTag("compare").performScrollToNode(hasTestTag("option-car2_dryyear_safflower"))
        compose.onNodeWithText("Dry-year safflower").assertIsDisplayed()
        compose.onNodeWithTag("compare").performScrollToNode(hasTestTag("see-all"))
        compose.onNodeWithTag("see-all").performClick()
        assertEquals(1, toggled)
    }
}
