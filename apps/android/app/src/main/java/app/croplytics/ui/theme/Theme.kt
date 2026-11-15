package app.croplytics.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.ui.unit.dp

private fun scheme(t: CropLyticsColors) = if (t.isDark) {
    darkColorScheme(
        primary = t.accent, onPrimary = t.onAccent, secondary = t.accent, onSecondary = t.onAccent,
        tertiary = t.warn, background = t.paper, onBackground = t.text, surface = t.paper, onSurface = t.text,
        surfaceVariant = t.panel2, onSurfaceVariant = t.muted, surfaceContainer = t.panel2, surfaceContainerLow = t.paper,
        surfaceContainerHigh = t.panel2, surfaceContainerHighest = t.panel2, outline = t.line, outlineVariant = t.lineSoft,
        error = t.bad, onError = t.paper,
        primaryContainer = t.panel2, onPrimaryContainer = t.text, secondaryContainer = t.panel2, onSecondaryContainer = t.text,
        tertiaryContainer = t.panel2, onTertiaryContainer = t.warn, surfaceTint = t.paper,
    )
} else {
    lightColorScheme(
        primary = t.accent, onPrimary = t.onAccent, secondary = t.accent, onSecondary = t.onAccent,
        tertiary = t.warn, background = t.paper, onBackground = t.text, surface = t.paper, onSurface = t.text,
        surfaceVariant = t.panel2, onSurfaceVariant = t.muted, surfaceContainer = t.panel2, surfaceContainerLow = t.paper,
        surfaceContainerHigh = t.panel2, surfaceContainerHighest = t.panel2, outline = t.line, outlineVariant = t.lineSoft,
        error = t.bad, onError = t.paper,
        primaryContainer = t.panel2, onPrimaryContainer = t.text, secondaryContainer = t.panel2, onSecondaryContainer = t.text,
        tertiaryContainer = t.panel2, onTertiaryContainer = t.warn, surfaceTint = t.paper,
    )
}

/** Small radii (2-4 dp), as printed panels; no rounded pills. */
private val shapes = Shapes(
    extraSmall = RoundedCornerShape(2.dp),
    small = RoundedCornerShape(3.dp),
    medium = RoundedCornerShape(4.dp),
    large = RoundedCornerShape(4.dp),
    extraLarge = RoundedCornerShape(6.dp),
)

@Composable
fun CropLyticsTheme(darkTheme: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    // No dynamic colour: the bulletin palette is the product's look.
    val tokens = if (darkTheme) DarkTokens else LightTokens
    CompositionLocalProvider(LocalCropLyticsColors provides tokens) {
        MaterialTheme(colorScheme = scheme(tokens), typography = CropLyticsTypography, shapes = shapes, content = content)
    }
}

object CropLyticsTheme {
    val colors: CropLyticsColors
        @Composable @ReadOnlyComposable get() = LocalCropLyticsColors.current
}
