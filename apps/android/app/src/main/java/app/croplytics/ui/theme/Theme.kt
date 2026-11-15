package app.croplytics.ui.theme

import android.provider.Settings
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.LocalRippleConfiguration
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RippleConfiguration
import androidx.compose.material3.Shapes
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.material.ripple.RippleAlpha
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.compositionLocalOf
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp

/** Platform mapping from docs/ui-redesign-spec.md 3.8: container = the tonal selected state for stock M3 controls. */
private fun scheme(t: CropLyticsColors) = (if (t.isDark) darkColorScheme() else lightColorScheme()).copy(
    primary = t.accent, onPrimary = t.onAccent,
    primaryContainer = t.accentContainer, onPrimaryContainer = t.onAccentContainer,
    secondary = t.accent, onSecondary = t.onAccent,
    secondaryContainer = t.accentContainer, onSecondaryContainer = t.onAccentContainer,
    tertiary = t.warn, tertiaryContainer = t.warnContainer, onTertiaryContainer = t.onWarnContainer,
    background = t.paper, onBackground = t.text, surface = t.paper, onSurface = t.text,
    surfaceVariant = t.panel2, onSurfaceVariant = t.text2,
    surfaceContainerLowest = t.raised, surfaceContainerLow = t.paper, surfaceContainer = t.panel2, surfaceContainerHigh = t.panel2, surfaceContainerHighest = t.panel2,
    surfaceTint = t.paper, outline = t.outline, outlineVariant = t.line, error = t.bad, onError = t.paper,
)

/** Rounded where you touch it, square where you read it: 4 / 8 / 12 / 16 / 20; pills use CircleShape. */
private val shapes = Shapes(
    extraSmall = RoundedCornerShape(4.dp), small = RoundedCornerShape(8.dp), medium = RoundedCornerShape(12.dp),
    large = RoundedCornerShape(16.dp), extraLarge = RoundedCornerShape(20.dp),
)

/** True when the grower turned animations off ("Remove animations"): every transition snaps. */
val LocalReduceMotion = compositionLocalOf { false }

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CropLyticsTheme(darkTheme: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    val tokens = if (darkTheme) DarkTokens else LightTokens
    val context = LocalContext.current
    val reduce = remember { runCatching { Settings.Global.getFloat(context.contentResolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f) == 0f }.getOrDefault(false) }
    // ink state layers: 10% pressed, 5% hover (spec 2.3)
    val ripple = RippleConfiguration(color = tokens.text, rippleAlpha = RippleAlpha(draggedAlpha = 0.10f, focusedAlpha = 0.10f, hoveredAlpha = 0.05f, pressedAlpha = 0.10f))
    CompositionLocalProvider(LocalCropLyticsColors provides tokens, LocalReduceMotion provides reduce, LocalRippleConfiguration provides ripple) {
        MaterialTheme(colorScheme = scheme(tokens), typography = CropLyticsTypography, shapes = shapes, content = content)
    }
}

object CropLyticsTheme {
    val colors: CropLyticsColors
        @Composable @ReadOnlyComposable get() = LocalCropLyticsColors.current
}
