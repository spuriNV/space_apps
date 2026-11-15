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
    /** Sunken: search field, disclosure row, segmented track. */
    val panel2: Color,
    /** Cards on paper, segmented thumb. */
    val raised: Color,
    val headBand: Color,
    val headInk: Color,
    val headInk2: Color,
    val text: Color,
    val text2: Color,
    val muted: Color,
    /** Row dividers. */
    val line: Color,
    /** Card edges. */
    val lineSoft: Color,
    /** Chip and input boundaries that must be seen (3:1). */
    val outline: Color,
    val accent: Color,
    val onAccent: Color,
    /** The selected state: a tonal fill, never a slab of green. */
    val accentContainer: Color,
    val accentContainerHover: Color,
    val onAccentContainer: Color,
    /** Check icon, the ring on the current thumbnail. */
    val accentOutline: Color,
    val good: Color,
    val warn: Color,
    val bad: Color,
    val warnContainer: Color,
    val onWarnContainer: Color,
    val mark: Color,
    val track: Color,
    /** Ink state layers: hover 5%, pressed 10%, strong 14% (dark: 6 / 12 / 16%). */
    val stateHover: Color,
    val statePressed: Color,
    val stateStrong: Color,
    val isDark: Boolean,
)

/** docs/ui-redesign-spec.md 3.1 (light). */
val LightTokens = CropLyticsColors(
    paper = Color(0xFFF7F6F0), panel2 = Color(0xFFEFEEE7), raised = Color(0xFFFFFFFF),
    headBand = Color(0xFF2F5D34), headInk = Color(0xFFFFFFFF), headInk2 = Color(0xFFDFE9DC),
    text = Color(0xFF191C16), text2 = Color(0xFF363A31), muted = Color(0xFF5A5E54),
    line = Color(0x24191C16), lineSoft = Color(0x14191C16), outline = Color(0xFF84877D),
    accent = Color(0xFF2F5D34), onAccent = Color(0xFFFFFFFF),
    accentContainer = Color(0xFFE3ECDD), accentContainerHover = Color(0xFFD7E4D0), onAccentContainer = Color(0xFF1D3A21), accentOutline = Color(0xFF5F8A5C),
    good = Color(0xFF2F5D34), warn = Color(0xFF8A5A00), bad = Color(0xFFA12A1C), warnContainer = Color(0xFFF4EAD6), onWarnContainer = Color(0xFF6B4600),
    mark = Color(0xFF191C16), track = Color(0x17191C16),
    stateHover = Color(0x0D191C16), statePressed = Color(0x1A191C16), stateStrong = Color(0x24191C16),
    isDark = false,
)

/** docs/ui-redesign-spec.md 3.2 (dark): used when the phone is in dark mode. */
val DarkTokens = CropLyticsColors(
    paper = Color(0xFF171A15), panel2 = Color(0xFF20241D), raised = Color(0xFF23281F),
    headBand = Color(0xFF9FCB9B), headInk = Color(0xFF10260F), headInk2 = Color(0xFF10260F),
    text = Color(0xFFECEBE3), text2 = Color(0xFFC9CBC0), muted = Color(0xFFA3A69A),
    line = Color(0x29ECEBE3), lineSoft = Color(0x17ECEBE3), outline = Color(0xFF6C7066),
    accent = Color(0xFF9FCB9B), onAccent = Color(0xFF10260F),
    accentContainer = Color(0xFF2B3F2B), accentContainerHover = Color(0xFF344C34), onAccentContainer = Color(0xFFCFE6C9), accentOutline = Color(0xFF7FAE7B),
    good = Color(0xFF9FCB9B), warn = Color(0xFFE0B04A), bad = Color(0xFFF08A7A), warnContainer = Color(0xFF3A2F17), onWarnContainer = Color(0xFFF0D59A),
    mark = Color(0xFFECEBE3), track = Color(0x24ECEBE3),
    stateHover = Color(0x0FECEBE3), statePressed = Color(0x1FECEBE3), stateStrong = Color(0x29ECEBE3),
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
