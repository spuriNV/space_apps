package app.croplytics

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import app.croplytics.ui.app.MainScreen
import app.croplytics.ui.theme.CropLyticsTheme
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    /** croplytics://field/<id>?tab=<0-4>: 0 field now, 1 coming season, 2 this field's year, 3 compare, 4 print. */
    private var deepLink by mutableStateOf<Pair<String, Int>?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        if (savedInstanceState == null) deepLink = parse(intent)
        setContent { CropLyticsTheme { MainScreen(deepLink) } }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        parse(intent)?.let { deepLink = it }
    }

    private fun parse(intent: Intent?): Pair<String, Int>? {
        val uri = intent?.data ?: return null
        if (uri.scheme != "croplytics" || uri.host != "field") return null
        val id = uri.pathSegments.firstOrNull() ?: return null
        return id to (uri.getQueryParameter("tab")?.toIntOrNull() ?: 0)
    }
}
