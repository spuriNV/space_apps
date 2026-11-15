package app.croplytics

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import app.croplytics.ui.navigation.CropLyticsNavHost
import app.croplytics.ui.theme.CropLyticsTheme
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        setContent {
            CropLyticsTheme {
                CropLyticsNavHost()
            }
        }
    }
}
