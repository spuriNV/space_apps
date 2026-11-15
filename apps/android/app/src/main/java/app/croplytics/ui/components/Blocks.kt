package app.croplytics.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import app.croplytics.domain.Answer
import app.croplytics.ui.theme.CropLyticsTheme

/** Green header band with a page title in white slab and one lede line. */
@Composable
fun HeadBand(title: String, lede: String?, modifier: Modifier = Modifier) {
    val c = CropLyticsTheme.colors
    Column(
        modifier
            .fillMaxWidth()
            .background(c.headBand)
            .padding(horizontal = 16.dp, vertical = 14.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Text(title, style = MaterialTheme.typography.titleLarge, color = c.headInk, modifier = Modifier.semantics { heading() })
        if (lede != null) Text(lede, style = MaterialTheme.typography.bodyMedium, color = c.headInk2)
    }
}

/** Section heading: 2 dp ink rule above, slab face, sentence case. */
@Composable
fun SectionHeading(text: String, modifier: Modifier = Modifier, sub: String? = null) {
    val c = CropLyticsTheme.colors
    Column(modifier.fillMaxWidth().padding(horizontal = 16.dp)) {
        Box(Modifier.fillMaxWidth().height(2.dp).background(c.text))
        Spacer(Modifier.height(8.dp))
        Text(text, style = MaterialTheme.typography.titleMedium, color = c.text, modifier = Modifier.semantics { heading() })
        if (sub != null) Text(sub, style = MaterialTheme.typography.bodySmall, color = c.muted)
    }
}

/** One source line: instrument in plain words, scale in miles, status. */
@Composable
fun Cite(text: String, modifier: Modifier = Modifier) {
    Text(text, modifier, style = MaterialTheme.typography.labelSmall, color = CropLyticsTheme.colors.muted)
}

/** "What's this?": opens a plain explanation from the glossary. */
@Composable
fun WhatsThis(onClick: () -> Unit) {
    Text(
        "What's this?",
        style = MaterialTheme.typography.labelMedium.copy(textDecoration = TextDecoration.Underline),
        color = CropLyticsTheme.colors.accent,
        modifier = Modifier
            .heightIn(min = 32.dp)
            .clickable(role = Role.Button, onClickLabel = "Explain", onClick = onClick)
            .padding(vertical = 6.dp),
    )
}

/** A question, its plain answer, the numbers in a sentence and one source line. */
@Composable
fun AnswerBlock(answer: Answer, modifier: Modifier = Modifier, onWhatsThis: (() -> Unit)? = null) {
    val c = CropLyticsTheme.colors
    Column(modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(answer.question, style = MaterialTheme.typography.bodySmall, color = c.muted)
        Text(answer.headline, style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.SemiBold), color = if (answer.warn) c.warn else c.text)
        if (answer.detail.isNotBlank()) Text(answer.detail, style = MaterialTheme.typography.bodyMedium, color = c.text2)
        Cite(answer.cite)
        if (onWhatsThis != null) WhatsThis(onWhatsThis)
    }
}

/** A full-width action: title, one-line description, chevron because it opens a view. */
@Composable
fun ActionRow(title: String, description: String, primary: Boolean = false, onClick: () -> Unit) {
    val c = CropLyticsTheme.colors
    Row(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 4.dp)
            .then(if (primary) Modifier.background(c.accent, RoundedCornerShape(3.dp)) else Modifier.border(1.dp, c.line, RoundedCornerShape(3.dp)))
            .clickable(role = Role.Button, onClick = onClick)
            .heightIn(min = 56.dp)
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.labelLarge, color = if (primary) c.onAccent else c.text)
            Text(description, style = MaterialTheme.typography.bodySmall, color = if (primary) c.onAccent.copy(alpha = 0.85f) else c.muted)
        }
        Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = null, tint = if (primary) c.onAccent else c.muted)
    }
}

/** Collapsed "More detail" section: everything a farmer doesn't need to decide. */
@Composable
fun MoreDetail(title: String, summary: String? = null, initiallyOpen: Boolean = false, content: @Composable () -> Unit) {
    val c = CropLyticsTheme.colors
    var open by rememberSaveable(title) { mutableStateOf(initiallyOpen) }
    Column(Modifier.fillMaxWidth().testTag("detail-$title")) {
        HorizontalDivider(color = c.lineSoft)
        Row(
            Modifier
                .fillMaxWidth()
                .clickable(role = Role.Button, onClickLabel = if (open) "Hide" else "Show") { open = !open }
                .semantics { stateDescription = if (open) "Shown" else "Hidden" }
                .heightIn(min = 52.dp)
                .padding(horizontal = 16.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text(title, style = MaterialTheme.typography.titleSmall, color = c.text)
                if (summary != null) Text(summary, style = MaterialTheme.typography.bodySmall, color = c.muted)
            }
            Icon(Icons.Filled.KeyboardArrowDown, contentDescription = null, tint = c.muted, modifier = Modifier.rotate(if (open) 180f else 0f))
        }
        AnimatedVisibility(open) {
            Column(Modifier.fillMaxWidth().padding(start = 16.dp, end = 16.dp, bottom = 14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                content()
            }
        }
    }
}

/** Label at the left in muted, value in ink. */
@Composable
fun LabelValue(label: String, value: String, modifier: Modifier = Modifier, warn: Boolean = false) {
    val c = CropLyticsTheme.colors
    Row(modifier.fillMaxWidth().padding(vertical = 2.dp)) {
        Text(label, Modifier.width(104.dp), style = MaterialTheme.typography.bodySmall, color = c.muted)
        Text(value, Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium, color = if (warn) c.warn else c.text)
    }
}

@Composable
fun BodyText(text: String, modifier: Modifier = Modifier) =
    Text(text, modifier, style = MaterialTheme.typography.bodyMedium, color = CropLyticsTheme.colors.text2)

/** "Example, change to yours": italic warn colour with a hatched square. */
@Composable
fun ExampleNote(text: String = "example, change to yours") {
    val c = CropLyticsTheme.colors
    Row(verticalAlignment = Alignment.CenterVertically) {
        Hatch(Modifier.size(11.dp), c.warn)
        Spacer(Modifier.width(6.dp))
        Text(text, style = MaterialTheme.typography.bodySmall.copy(fontStyle = FontStyle.Italic), color = c.warn)
    }
}

/** Part of a "More detail" section that could not load. */
@Composable
fun DetailUnavailable(text: String) = Text(text, style = MaterialTheme.typography.bodySmall, color = CropLyticsTheme.colors.muted)
