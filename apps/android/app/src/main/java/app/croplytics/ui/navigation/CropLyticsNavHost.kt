package app.croplytics.ui.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navDeepLink
import androidx.navigation.toRoute
import app.croplytics.ui.field.FieldScreen
import app.croplytics.ui.fields.FieldsScreen
import app.croplytics.ui.map.FieldMapScreen
import kotlinx.serialization.Serializable

@Serializable
data object FieldsRoute

/** One field; [tab] is the section to open (0 field now, 1 coming season, 2 compare, 3 adviser summary). */
@Serializable
data class FieldRoute(val id: String, val tab: Int = 0)

@Serializable
data class MapRoute(val id: String)

const val DEEP_LINK_BASE = "croplytics://field"

@Composable
fun CropLyticsNavHost() {
    val nav = rememberNavController()
    NavHost(nav, startDestination = FieldsRoute) {
        composable<FieldsRoute> {
            FieldsScreen(onOpenField = { nav.navigate(FieldRoute(it)) })
        }
        // croplytics://field/car_colusa_rice?tab=2 opens Compare for that field
        composable<FieldRoute>(deepLinks = listOf(navDeepLink<FieldRoute>(basePath = DEEP_LINK_BASE))) { entry ->
            val route = entry.toRoute<FieldRoute>()
            FieldScreen(
                initialTab = route.tab,
                onBack = { if (!nav.popBackStack()) nav.navigate(FieldsRoute) { popUpTo(0) } },
                onOpenMap = { nav.navigate(MapRoute(it)) },
            )
        }
        composable<MapRoute> {
            FieldMapScreen(onBack = { nav.popBackStack() })
        }
    }
}
