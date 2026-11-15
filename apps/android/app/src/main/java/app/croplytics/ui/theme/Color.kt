package app.croplytics.ui.theme

import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color

/**
 * "Extension bulletin" palette (.claude/skills/fieldshift-visual-design): paper, black ink, one spot
 * green, brown only for example numbers and over-the-limit, red for problems. Components read these
 * tokens; hex values appear only here and for the fixed data colours.
 */
@Immutable
data class CropLyticsColors(
    val paper: Color,
    val panel2: Color,
    val headBand: Color,
    val headInk: Color,
    val headInk2: Color,
    val text: Color,
    val text2: Color,
    val muted: Color,
    val line: Color,
    val lineSoft: Color,
    val accent: Color,
    val onAccent: Color,
    val good: Color,
    val warn: Color,
    val bad: Color,
    val mark: Color,
    val track: Color,
    val isDark: Boolean,
)

val LightTokens = CropLyticsColors(
    paper = Color(0xFFF7F6F0),
    panel2 = Color(0xFFEBEAE0),
    headBand = Color(0xFF2F5D34),
    headInk = Color(0xFFFFFFFF),
    headInk2 = Color(0xFFDFE9DC),
    text = Color(0xFF191C16),
    text2 = Color(0xFF363A31),
    muted = Color(0xFF5A5E54), // 6.1:1 on paper
    line = Color(0x42191C16),
    lineSoft = Color(0x1F191C16),
    accent = Color(0xFF2F5D34),
    onAccent = Color(0xFFFFFFFF),
    good = Color(0xFF2F5D34),
    warn = Color(0xFF8A5A00), // 5.6:1 on paper
    bad = Color(0xFFA12A1C),
    mark = Color(0xFF191C16),
    track = Color(0x17191C16),
    isDark = false,
)

/** Dark paper: the same two-colour print, inverted, with the spot green lifted for contrast. */
val DarkTokens = CropLyticsColors(
    paper = Color(0xFF141712),
    panel2 = Color(0xFF1E221C),
    headBand = Color(0xFF244A29),
    headInk = Color(0xFFFFFFFF),
    headInk2 = Color(0xFFCFE0CB),
    text = Color(0xFFECEBE3),
    text2 = Color(0xFFD3D4CA),
    muted = Color(0xFFA7AB9E),
    line = Color(0x52ECEBE3),
    lineSoft = Color(0x24ECEBE3),
    accent = Color(0xFF8CC495),
    onAccent = Color(0xFF0E2411),
    good = Color(0xFF8CC495),
    warn = Color(0xFFE2B45C),
    bad = Color(0xFFF08F7D),
    mark = Color(0xFFECEBE3),
    track = Color(0x24ECEBE3),
    isDark = true,
)

/** Fixed data colours (web lib.ts): never reused for chrome. */
object DataColors {
    val bare = Color(0xFFA8703F)
    val partial = Color(0xFFB7D77A)
    val covered = Color(0xFF2F9E4B)
    val water = Color(0xFF3D97E8)
    val unknown = Color(0xFFBDBDBD)
    val soil = Color(0xFF8A5A2B)
    val groundwater = Color(0xFF1F6FB8)
    val selection = Color(0xFFFFD166)

    fun crop(name: String): Color = when {
        name.startsWith("Rice") -> Color(0xFF3D7FC4)
        name == "Left fallow" -> Color(0xFFB08A5A)
        name.startsWith("Alfalfa") -> Color(0xFF4F8F3A)
        name.startsWith("Corn") -> Color(0xFFD4B23C)
        name.startsWith("Wheat") -> Color(0xFFC79A3A)
        else -> Color(0xFF8A8A80)
    }
}

val LocalCropLyticsColors = staticCompositionLocalOf { LightTokens }
