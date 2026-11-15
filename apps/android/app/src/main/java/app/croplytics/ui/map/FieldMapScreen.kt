package app.croplytics.ui.map

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import app.croplytics.ui.components.FieldMap
import app.croplytics.ui.field.FieldViewModel
import app.croplytics.ui.theme.CropLyticsTheme

/** Full-screen satellite map of the field. Labels sit in solid paper boxes, never straight on imagery. */
@Composable
fun FieldMapScreen(onBack: () -> Unit, viewModel: FieldViewModel = hiltViewModel()) {
    val c = CropLyticsTheme.colors
    val header by viewModel.header.collectAsStateWithLifecycle()
    Box(Modifier.fillMaxSize()) {
        if (header.rings.isNotEmpty()) FieldMap(header.rings, interactive = true, modifier = Modifier.fillMaxSize(), paddingDp = 72)
        Surface(
            modifier = Modifier.statusBarsPadding().padding(12.dp).align(Alignment.TopStart),
            shape = RoundedCornerShape(2.dp), color = c.paper, border = androidx.compose.foundation.BorderStroke(1.dp, c.text), shadowElevation = 2.dp,
        ) {
            IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back to the field", tint = c.text) }
        }
        header.identity?.let { id ->
            Surface(
                modifier = Modifier.navigationBarsPadding().padding(12.dp).align(Alignment.BottomStart),
                shape = RoundedCornerShape(2.dp), color = c.paper, border = androidx.compose.foundation.BorderStroke(1.dp, c.text), shadowElevation = 2.dp,
            ) {
                Column(Modifier.padding(horizontal = 12.dp, vertical = 8.dp)) {
                    Text(id.name, style = MaterialTheme.typography.titleSmall, color = c.text)
                    Text("Yellow line: the field's outline (state crop map). ${id.acres ?: "?"} acres.", style = MaterialTheme.typography.labelSmall, color = c.muted)
                }
            }
        }
    }
}
