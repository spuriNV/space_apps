package app.croplytics.ui.summary

import android.content.Context
import android.content.Intent
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Typeface
import android.graphics.pdf.PdfDocument
import android.os.Build
import android.text.Layout
import android.text.StaticLayout
import android.text.TextPaint
import androidx.core.content.FileProvider
import androidx.core.content.res.ResourcesCompat
import app.croplytics.R
import app.croplytics.domain.AdviserSummary
import app.croplytics.domain.Fmt
import java.io.File

/**
 * Draws the adviser summary on US Letter pages (612 x 792 pt) with Android's PdfDocument, in the
 * app's own typefaces, and shares it through the Android share sheet.
 */
object SummaryPdf {
    private const val PAGE_W = 612
    private const val PAGE_H = 792
    private const val MARGIN = 44f
    private const val INK = 0xFF191C16.toInt()
    private const val MUTED = 0xFF5A5E54.toInt()
    private const val GREEN = 0xFF2F5D34.toInt()
    private const val WARN = 0xFF8A5A00.toInt()

    fun write(context: Context, s: AdviserSummary): File {
        val slab = ResourcesCompat.getFont(context, R.font.zilla_slab_semibold) ?: Typeface.SERIF
        val franklin = ResourcesCompat.getFont(context, R.font.libre_franklin) ?: Typeface.SANS_SERIF
        val franklinBold = if (Build.VERSION.SDK_INT >= 28) Typeface.create(franklin, 650, false) else Typeface.create(franklin, Typeface.BOLD)
        val doc = PdfDocument()
        val w = PAGE_W - 2 * MARGIN
        var pageNo = 0
        lateinit var page: PdfDocument.Page
        lateinit var canvas: Canvas
        var y = 0f

        fun paint(tf: Typeface, size: Float, color: Int) = TextPaint(Paint.ANTI_ALIAS_FLAG).apply { typeface = tf; textSize = size; this.color = color }
        fun footer() {
            val p = paint(franklin, 7.5f, MUTED)
            canvas.drawText("CropLytics, NASA Space Apps 2026. Supports, doesn't replace, your adviser. Prepared ${s.preparedOn}. Page $pageNo.", MARGIN, PAGE_H - 24f, p)
        }
        fun newPage() {
            if (pageNo > 0) { footer(); doc.finishPage(page) }
            pageNo++
            page = doc.startPage(PdfDocument.PageInfo.Builder(PAGE_W, PAGE_H, pageNo).create())
            canvas = page.canvas
            y = MARGIN
        }
        fun text(t: String, p: TextPaint, after: Float = 3f, indent: Float = 0f) {
            val layout = StaticLayout.Builder.obtain(t, 0, t.length, p, (w - indent).toInt()).setAlignment(Layout.Alignment.ALIGN_NORMAL).setLineSpacing(0f, 1.12f).build()
            if (y + layout.height > PAGE_H - 46f) newPage()
            canvas.save(); canvas.translate(MARGIN + indent, y); layout.draw(canvas); canvas.restore()
            y += layout.height + after
        }
        fun heading(t: String) {
            if (y + 40 > PAGE_H - 46f) newPage()
            y += 6f
            canvas.drawRect(MARGIN, y, MARGIN + w, y + 1.5f, Paint().apply { color = INK })
            y += 6f
            text(t, paint(slab, 12.5f, INK), after = 3f)
        }

        newPage()
        // green header band with the field
        canvas.drawRect(0f, 0f, PAGE_W.toFloat(), 82f, Paint().apply { color = GREEN })
        canvas.drawText("Rotation summary for your adviser", MARGIN, 30f, paint(franklin, 9f, 0xFFDFE9DC.toInt()))
        canvas.drawText(s.fieldName, MARGIN, 54f, paint(slab, 19f, 0xFFFFFFFF.toInt()))
        canvas.drawText(s.fieldLine + (s.stateFieldNo?.let { ". State field no. $it" } ?: ""), MARGIN, 71f, paint(franklin, 9f, 0xFFDFE9DC.toInt()))
        y = 98f

        val body = paint(franklin, 9f, INK)
        val bold = paint(franklinBold, 9.5f, INK)
        val cite = paint(franklin, 7.5f, MUTED)

        heading("This season so far")
        s.now.forEach { a ->
            text(a.headline, if (a.warn) paint(franklinBold, 9.5f, WARN) else bold, after = 1f)
            text(a.detail, body, after = 1f)
            text(a.cite, cite, after = 5f)
        }
        heading("What's likely this coming season (outlooks, not forecasts)")
        s.season.forEach { a ->
            text(a.headline, if (a.warn) paint(franklinBold, 9.5f, WARN) else bold, after = 1f)
            text(a.detail, body, after = 5f)
        }
        heading("The option to talk through")
        text("Today: ${s.today}", body, after = 3f)
        s.option?.let { o ->
            text(o.name + (o.need?.let { ", about ${Fmt.one(it.value)} acre-ft/acre a year" } ?: ""), bold, after = 2f)
            text("Gains: " + (o.gains.joinToString("; ") { "${it.title.lowercase()}, ${it.amount}" }.ifEmpty { "nothing clear" }) + ".", body, after = 2f)
            text("Gives up: " + (o.giveUps.joinToString("; ") { "${it.title.lowercase()}, ${it.amount}" }.ifEmpty { "nothing clear" }) + ".", body, after = 2f)
            if (o.unclear.isNotEmpty()) text("No clear difference: ${o.unclear.joinToString(", ")}.", body, after = 2f)
        } ?: text("No alternative worked out for this field yet.", body)
        s.limitLine?.let { text(it, cite, after = 3f) }
        heading("What to check locally")
        s.checkLocally.forEach { text("• $it", body, after = 2f, indent = 4f) }
        heading("Sources")
        text(s.sources.joinToString("; ") + ".", cite, after = 2f)

        footer()
        doc.finishPage(page)
        val dir = File(context.cacheDir, "summaries").apply { mkdirs() }
        val file = File(dir, s.fileName)
        file.outputStream().use { doc.writeTo(it) }
        doc.close()
        return file
    }

    fun shareIntent(context: Context, file: File, title: String): Intent {
        val uri = FileProvider.getUriForFile(context, "${context.packageName}.files", file)
        val send = Intent(Intent.ACTION_SEND).apply {
            type = "application/pdf"
            putExtra(Intent.EXTRA_STREAM, uri)
            putExtra(Intent.EXTRA_SUBJECT, title)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        return Intent.createChooser(send, "Share the summary")
    }
}
