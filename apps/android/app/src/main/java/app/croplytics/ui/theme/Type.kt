package app.croplytics.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontVariation
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.LineHeightStyle
import androidx.compose.ui.unit.sp
import app.croplytics.R

/** Zilla Slab for headings, place names and answers: slab like the farm bulletins growers read. */
val ZillaSlab = FontFamily(
    Font(R.font.zilla_slab_medium, FontWeight.Medium),
    Font(R.font.zilla_slab_semibold, FontWeight.SemiBold),
)

/** Libre Franklin (variable) for UI, data and source lines: Franklin Gothic, the workhorse of farm print. */
@OptIn(androidx.compose.ui.text.ExperimentalTextApi::class)
val LibreFranklin = FontFamily(
    Font(R.font.libre_franklin, FontWeight.Normal, variationSettings = FontVariation.Settings(FontVariation.weight(400))),
    Font(R.font.libre_franklin, FontWeight.SemiBold, variationSettings = FontVariation.Settings(FontVariation.weight(600))),
    Font(R.font.libre_franklin, FontWeight.Bold, variationSettings = FontVariation.Settings(FontVariation.weight(700))),
)

private val tight = LineHeightStyle(LineHeightStyle.Alignment.Center, LineHeightStyle.Trim.None)

/** All sizes in sp so the grower's font-size setting scales every line. */
val CropLyticsTypography = Typography(
    headlineMedium = TextStyle(fontFamily = ZillaSlab, fontWeight = FontWeight.SemiBold, fontSize = 26.sp, lineHeight = 30.sp),
    headlineSmall = TextStyle(fontFamily = ZillaSlab, fontWeight = FontWeight.SemiBold, fontSize = 22.sp, lineHeight = 27.sp),
    titleLarge = TextStyle(fontFamily = ZillaSlab, fontWeight = FontWeight.SemiBold, fontSize = 20.sp, lineHeight = 25.sp),
    titleMedium = TextStyle(fontFamily = ZillaSlab, fontWeight = FontWeight.SemiBold, fontSize = 18.sp, lineHeight = 23.sp),
    titleSmall = TextStyle(fontFamily = ZillaSlab, fontWeight = FontWeight.Medium, fontSize = 17.sp, lineHeight = 22.sp),
    bodyLarge = TextStyle(fontFamily = LibreFranklin, fontWeight = FontWeight.Normal, fontSize = 16.sp, lineHeight = 23.sp),
    bodyMedium = TextStyle(fontFamily = LibreFranklin, fontWeight = FontWeight.Normal, fontSize = 14.sp, lineHeight = 20.sp),
    bodySmall = TextStyle(fontFamily = LibreFranklin, fontWeight = FontWeight.Normal, fontSize = 13.sp, lineHeight = 18.sp, lineHeightStyle = tight),
    labelLarge = TextStyle(fontFamily = LibreFranklin, fontWeight = FontWeight.SemiBold, fontSize = 15.sp, lineHeight = 20.sp),
    labelMedium = TextStyle(fontFamily = LibreFranklin, fontWeight = FontWeight.SemiBold, fontSize = 13.sp, lineHeight = 17.sp),
    labelSmall = TextStyle(fontFamily = LibreFranklin, fontWeight = FontWeight.Normal, fontSize = 12.sp, lineHeight = 16.sp),
)
