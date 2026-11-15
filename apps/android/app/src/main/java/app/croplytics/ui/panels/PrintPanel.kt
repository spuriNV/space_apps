package app.croplytics.ui.panels

import android.content.Context
import android.content.Intent
import android.graphics.Paint
import android.graphics.Typeface
import android.graphics.pdf.PdfDocument
import android.os.Build
import android.os.Bundle
import android.os.CancellationSignal
import android.os.ParcelFileDescriptor
import android.print.PageRange
import android.print.PrintAttributes
import android.print.PrintDocumentAdapter
import android.print.PrintDocumentInfo
import android.print.PrintManager
import android.text.Layout
import android.text.StaticLayout
import android.text.TextPaint
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import androidx.core.content.res.ResourcesCompat
import app.croplytics.R
import app.croplytics.data.repository.dataOrNull
import app.croplytics.domain.BriefLogic
import app.croplytics.domain.CompareLogic
import app.croplytics.domain.Timeline
import app.croplytics.ui.app.FieldData
import app.croplytics.ui.app.MainUiState
import app.croplytics.ui.components.PageSkeleton
import app.croplytics.ui.components.clsColor
import app.croplytics.ui.theme.CropLyticsTheme
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

/** "Print for your adviser" (RotationBrief.tsx): one Letter page, shared or printed as a PDF. */
fun LazyListScope.printPanel(state: MainUiState, data: FieldData, pick: String?, onPick: (String) -> Unit) {
    val strategies = data.strategies.dataOrNull
    if (strategies.isNullOrEmpty()) { item(key = "pr-wait") { PageSkeleton() }; return }
    val brief = BriefLogic.build(data.item.loc, strategies, pick, data.limit ?: 3.0, data.exampleLimit, data.outlook.dataOrNull, data.nasaNow.dataOrNull,
        data.calendar.dataOrNull?.calendar, data.daily.dataOrNull, state.todayT, Timeline.fmtDate(java.time.LocalDate.now().toString())) ?: return
    item(key = "pr-rail") {
        val c = CropLyticsTheme.colors
        val context = LocalContext.current
        val scope = rememberCoroutineScope()
        Column(Modifier.fillMaxWidth().padding(16.dp).testTag("brief"), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Summary for your adviser", style = MaterialTheme.typography.titleLarge, color = c.text, modifier = Modifier.semantics { heading() })
            Text("One page, Letter size. Sentences are fixed templates filled with the model’s numbers, each with a source.", style = MaterialTheme.typography.bodySmall, color = c.muted)
            Text("Option to print", style = MaterialTheme.typography.labelMedium, color = c.text)
            Row(Modifier.horizontalScroll(rememberScrollState()).testTag("brief-pick"), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                strategies.forEach { s ->
                    val on = CompareLogic.shortName(s) == brief.option
                    Text(CompareLogic.shortName(s) + if (s.isBaseline) " (today)" else "",
                        Modifier.border(1.dp, if (on) c.accent else c.line, RoundedCornerShape(3.dp)).background(if (on) c.accent else c.paper).clickable { onPick(s.id) }
                            .semantics { selected = on }.heightIn(min = 40.dp).padding(horizontal = 10.dp, vertical = 10.dp), style = MaterialTheme.typography.labelMedium, color = if (on) c.onAccent else c.text)
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button({ scope.launch { val f = withContext(Dispatchers.IO) { BriefPdf.write(context, brief) }; context.startActivity(BriefPdf.share(context, f, brief.name)) } },
                    Modifier.weight(1f).heightIn(min = 48.dp).testTag("share-pdf"), shape = RoundedCornerShape(3.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = c.accent, contentColor = c.onAccent)) { Text("Share as PDF") }
                OutlinedButton({ scope.launch { val f = withContext(Dispatchers.IO) { BriefPdf.write(context, brief) }; BriefPdf.print(context, f, brief.name) } },
                    Modifier.weight(1f).heightIn(min = 48.dp), shape = RoundedCornerShape(3.dp)) { Text("Print") }
            }
        }
    }
    item(key = "pr-page") { BriefPage(brief) }
}

@Composable
private fun BriefPage(b: BriefLogic.Brief) {
    val c = CropLyticsTheme.colors
    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp).border(1.dp, c.line).background(c.paper)) {
        Column(Modifier.fillMaxWidth().background(c.headBand).padding(12.dp)) {
            Text("CropLytics summary for the grower and adviser · prepared ${b.prepared}", style = MaterialTheme.typography.labelSmall, color = c.headInk2)
            Text(b.name, style = MaterialTheme.typography.titleLarge, color = c.headInk)
            Text(b.sub, style = MaterialTheme.typography.labelSmall, color = c.headInk2)
            Text("Option looked at: ${b.option}${if (b.optionIsToday) " (what the field does now)" else ""}", style = MaterialTheme.typography.labelLarge, color = c.headInk)
        }
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            H("1. This field"); P(b.thisField)
            H("2. What’s likely this season (outlooks, not forecasts)"); b.likely.forEach { P("• $it") }
            H("3. The option: ${b.optionTitle}")
            Row(Modifier.fillMaxWidth()) { b.months.forEach { (m, cls, what) -> Column(Modifier.weight(1f)) { Text(m.take(1), style = MaterialTheme.typography.labelSmall, color = c.muted); Box(Modifier.fillMaxWidth().height(8.dp).background(clsColor(cls))) } } }
            P("${b.water} Status: ${b.waterStatus}.")
            var n = 4
            if (b.gains != null) {
                H("${n++}. What it gains over today"); b.gains.ifEmpty { listOf("Nothing clearly better.") }.forEach { P("• $it") }
                H("What it gives up"); (b.losses ?: emptyList()).ifEmpty { listOf("Nothing clearly worse.") }.forEach { P("• $it") }
                if (b.unclear.isNotEmpty()) P("Too close to call: ${b.unclear.joinToString(", ")}.")
            }
            H("${n++}. All rotations at a glance (typical year)")
            Table(listOf("Rotation", "Need, acre-ft/acre", "Limit", "Bare days", "Hot bare days"), b.table.map { listOf(it.name, it.need, it.against, it.bare, it.hotBare) })
            Text("Seen = satellite record for this field; est. = rotation model. * Upper bound: soil water stored over winter is not counted.", style = MaterialTheme.typography.labelSmall, color = c.muted)
            H("$n. Check locally before anything is seeded"); b.checks.forEach { (t, imp) -> P("☐ $t${if (imp) " (important)" else ""}") }
            Text("Sources. ${b.sources}", style = MaterialTheme.typography.labelSmall, color = c.muted)
            Text("This summary supports a conversation between grower and adviser; it does not replace one.", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold), color = c.text)
        }
    }
    Spacer(Modifier.height(16.dp))
}

@Composable private fun H(t: String) = Text(t, Modifier.padding(top = 6.dp).semantics { heading() }, style = MaterialTheme.typography.titleSmall, color = CropLyticsTheme.colors.text)
@Composable private fun P(t: String) = Text(t, style = MaterialTheme.typography.bodySmall, color = CropLyticsTheme.colors.text2)

/** The brief drawn on US Letter pages with PdfDocument, in the app's typefaces. */
object BriefPdf {
    private const val W = 612; private const val H = 792; private const val M = 40f
    fun write(context: Context, b: BriefLogic.Brief): File {
        val slab = ResourcesCompat.getFont(context, R.font.zilla_slab_semibold) ?: Typeface.SERIF
        val franklin = ResourcesCompat.getFont(context, R.font.libre_franklin) ?: Typeface.SANS_SERIF
        val bold = if (Build.VERSION.SDK_INT >= 28) Typeface.create(franklin, 650, false) else Typeface.create(franklin, Typeface.BOLD)
        fun paint(tf: Typeface, size: Float, color: Int) = TextPaint(Paint.ANTI_ALIAS_FLAG).apply { typeface = tf; textSize = size; this.color = color }
        val doc = PdfDocument(); var page = doc.startPage(PdfDocument.PageInfo.Builder(W, H, 1).create()); var canvas = page.canvas; var y = 0f; var no = 1
        val body = paint(franklin, 8.6f, 0xFF191C16.toInt()); val small = paint(franklin, 7.2f, 0xFF5A5E54.toInt()); val head = paint(slab, 11.5f, 0xFF191C16.toInt())
        fun newPage() { doc.finishPage(page); no++; page = doc.startPage(PdfDocument.PageInfo.Builder(W, H, no).create()); canvas = page.canvas; y = M }
        fun text(t: String, p: TextPaint, after: Float = 2f) {
            val l = StaticLayout.Builder.obtain(t, 0, t.length, p, (W - 2 * M).toInt()).setAlignment(Layout.Alignment.ALIGN_NORMAL).setLineSpacing(0f, 1.1f).build()
            if (y + l.height > H - M) newPage()
            canvas.save(); canvas.translate(M, y); l.draw(canvas); canvas.restore(); y += l.height + after
        }
        canvas.drawRect(0f, 0f, W.toFloat(), 86f, Paint().apply { color = 0xFF2F5D34.toInt() })
        canvas.drawText("CropLytics summary for the grower and adviser · prepared ${b.prepared}", M, 24f, paint(franklin, 8f, 0xFFDFE9DC.toInt()))
        canvas.drawText(b.name, M, 48f, paint(slab, 18f, 0xFFFFFFFF.toInt()))
        canvas.drawText(b.sub, M, 63f, paint(franklin, 8f, 0xFFDFE9DC.toInt()))
        canvas.drawText("Option looked at: ${b.option}${if (b.optionIsToday) " (what the field does now)" else ""}", M, 78f, paint(bold, 8.5f, 0xFFFFFFFF.toInt()))
        y = 100f
        text("1. This field", head); text(b.thisField, body, 6f)
        text("2. What’s likely this season (outlooks, not forecasts)", head); b.likely.forEach { text("• $it", body) }; y += 4
        text("3. The option: ${b.optionTitle}", head)
        val cw = (W - 2 * M) / 12
        b.months.forEachIndexed { i, (m, cls, _) ->
            canvas.drawText(m, M + i * cw, y + 7, small)
            canvas.drawRect(M + i * cw, y + 9, M + (i + 1) * cw - 1, y + 16, Paint().apply { color = android.graphics.Color.parseColor(app.croplytics.domain.Cls.COLOR[cls] ?: "#6b7280") })
        }
        y += 22
        text("${b.water} Status: ${b.waterStatus}.", body, 6f)
        var n = 4
        if (b.gains != null) {
            text("${n++}. What it gains over today", head); b.gains.ifEmpty { listOf("Nothing clearly better.") }.forEach { text("• $it", body) }
            text("What it gives up", head); (b.losses ?: emptyList()).ifEmpty { listOf("Nothing clearly worse.") }.forEach { text("• $it", body) }
            if (b.unclear.isNotEmpty()) text("Too close to call: ${b.unclear.joinToString(", ")}.", small, 6f)
        }
        text("${n++}. All rotations at a glance (typical year)", head)
        b.table.forEach { r -> text("${r.name}: ${r.need}; ${r.against}; bare ${r.bare} days; hot bare days ${r.hotBare}.", if (r.pick) paint(bold, 8.6f, 0xFF191C16.toInt()) else body) }
        text("Seen = satellite record for this field; est. = rotation model. * Upper bound: soil water stored over winter is not counted.", small, 6f)
        text("$n. Check locally before anything is seeded", head); b.checks.forEach { (t, imp) -> text("☐ $t${if (imp) " (important)" else ""}", body) }
        y += 4; text("Sources. ${b.sources}", small)
        text("This summary supports a conversation between grower and adviser; it does not replace one. CropLytics, made for the NASA Space Apps challenge “Field Shift: Adapting Farms with NASA Data”.", small)
        doc.finishPage(page)
        val dir = File(context.cacheDir, "summaries").apply { mkdirs() }
        val f = File(dir, "CropLytics summary - ${b.name.replace(Regex("[^A-Za-z0-9 .-]"), "").take(60)}.pdf")
        f.outputStream().use { doc.writeTo(it) }; doc.close()
        return f
    }

    fun share(context: Context, f: File, name: String): Intent {
        val uri = FileProvider.getUriForFile(context, "${context.packageName}.files", f)
        return Intent.createChooser(Intent(Intent.ACTION_SEND).apply {
            type = "application/pdf"; putExtra(Intent.EXTRA_STREAM, uri); putExtra(Intent.EXTRA_SUBJECT, "Rotation summary: $name"); addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }, "Share the summary")
    }

    /** Android's print dialog for the same PDF (the web's "Print or save as PDF"). */
    fun print(context: Context, f: File, name: String) {
        val pm = context.getSystemService(Context.PRINT_SERVICE) as PrintManager
        pm.print("CropLytics: $name", object : PrintDocumentAdapter() {
            override fun onLayout(old: PrintAttributes?, new: PrintAttributes?, cancel: CancellationSignal?, cb: LayoutResultCallback, extras: Bundle?) {
                if (cancel?.isCanceled == true) { cb.onLayoutCancelled(); return }
                cb.onLayoutFinished(PrintDocumentInfo.Builder(f.name).setContentType(PrintDocumentInfo.CONTENT_TYPE_DOCUMENT).build(), true)
            }
            override fun onWrite(pages: Array<out PageRange>?, dest: ParcelFileDescriptor, cancel: CancellationSignal?, cb: WriteResultCallback) {
                f.inputStream().use { input -> ParcelFileDescriptor.AutoCloseOutputStream(dest).use { input.copyTo(it) } }
                cb.onWriteFinished(arrayOf(PageRange.ALL_PAGES))
            }
        }, PrintAttributes.Builder().setMediaSize(PrintAttributes.MediaSize.NA_LETTER).build())
    }
}
