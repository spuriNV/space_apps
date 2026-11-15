package app.croplytics.ui.map

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.graphics.Typeface
import androidx.core.content.res.ResourcesCompat
import app.croplytics.R

/**
 * Field pins as bitmaps (MapView.tsx PIN_SVG): a paper-white map pin with a dark green edge and a crop-rows glyph, and a
 * solid paper label box with an ink border to its right ("never text straight on imagery"). The pin tip sits at the
 * bitmap's bottom centre, so the symbol anchors at "bottom"; the left half is transparent.
 */
object PinIcons {
    private const val INK = 0xFF191C16.toInt()
    private const val PAPER = 0xFFF7F6F0.toInt()
    private const val GREEN = 0xFF2F5D34.toInt()
    private const val MUTED = 0xFF5A5E54.toInt()

    fun pin(context: Context, selected: Boolean, bc: Boolean = false, title: String? = null, sub: String? = null): Bitmap {
        val d = context.resources.displayMetrics.density
        val pw = 28 * d; val ph = 36 * d
        val slab = ResourcesCompat.getFont(context, R.font.zilla_slab_semibold) ?: Typeface.SERIF
        val franklin = ResourcesCompat.getFont(context, R.font.libre_franklin) ?: Typeface.SANS_SERIF
        val tp = Paint(Paint.ANTI_ALIAS_FLAG).apply { typeface = slab; textSize = 13 * d; color = INK }
        val sp = Paint(Paint.ANTI_ALIAS_FLAG).apply { typeface = franklin; textSize = 11 * d; color = MUTED }
        val labelW = if (title != null) maxOf(tp.measureText(title), sub?.let { sp.measureText(it) } ?: 0f) + 16 * d else 0f
        val labelH = if (title != null) (if (sub != null) 38 else 24) * d else 0f
        val half = pw / 2 + (if (title != null) 4 * d + labelW else 0f)
        val w = (2 * half).toInt().coerceAtLeast(1); val h = maxOf(ph, labelH + 4 * d).toInt()
        val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        val c = Canvas(bmp)
        val x0 = half - pw / 2
        c.save(); c.translate(0f, h - ph) // the pin tip sits on the bottom edge
        if (bc) {
            // BC: a quiet dot, not a field pin (not set up yet)
            val p = Paint(Paint.ANTI_ALIAS_FLAG)
            p.color = 0xFF8A5A00.toInt(); c.drawCircle(half, ph - 9 * d, 7 * d, p)
            p.color = PAPER; c.drawCircle(half, ph - 9 * d, 3 * d, p)
        } else {
            val s = d
            val body = Path().apply {
                moveTo(x0 + 14 * s, 1.2f * s)
                cubicTo(x0 + 7.2f * s, 1.2f * s, x0 + 2 * s, 6.3f * s, x0 + 2 * s, 12.9f * s)
                cubicTo(x0 + 2 * s, 21.3f * s, x0 + 12.2f * s, 32.9f * s, x0 + 13.1f * s, 33.9f * s)
                cubicTo(x0 + 13.6f * s, 34.4f * s, x0 + 14.4f * s, 34.4f * s, x0 + 14.9f * s, 33.9f * s)
                cubicTo(x0 + 15.8f * s, 32.9f * s, x0 + 26 * s, 21.3f * s, x0 + 26 * s, 12.9f * s)
                cubicTo(x0 + 26 * s, 6.3f * s, x0 + 20.8f * s, 1.2f * s, x0 + 14 * s, 1.2f * s)
                close()
            }
            val fill = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = if (selected) GREEN else PAPER }
            val edge = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE; strokeWidth = 1.8f * s; color = if (selected) PAPER else GREEN }
            c.drawPath(body, fill); c.drawPath(body, edge)
            val glyph = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE; strokeWidth = 1.5f * s; color = if (selected) PAPER else GREEN }
            c.drawRoundRect(RectF(x0 + 8.5f * s, 7.5f * s, x0 + 19.5f * s, 18.5f * s), 1.5f * s, 1.5f * s, glyph)
            listOf(11f, 14f, 17f).forEach { gx -> c.drawLine(x0 + gx * s, 9.5f * s, x0 + gx * s, 16.5f * s, glyph) }
        }
        c.restore()
        if (title != null) {
            val lx = half + pw / 2 + 2 * d; val ly = 2 * d
            val box = RectF(lx, ly, lx + labelW, ly + labelH)
            c.drawRect(RectF(box.left + 1.5f * d, box.top + 1.5f * d, box.right + 1.5f * d, box.bottom + 1.5f * d), Paint().apply { color = 0x55000000 })
            c.drawRect(box, Paint().apply { color = PAPER })
            c.drawRect(box, Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE; strokeWidth = 1 * d; color = if (selected) GREEN else INK })
            c.drawText(title, lx + 8 * d, ly + 16 * d, tp)
            if (sub != null) c.drawText(sub, lx + 8 * d, ly + 31 * d, sp)
        }
        return bmp
    }
}
