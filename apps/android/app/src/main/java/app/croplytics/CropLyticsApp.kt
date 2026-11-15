package app.croplytics

import android.app.Application
import coil3.ImageLoader
import coil3.PlatformContext
import coil3.SingletonImageLoader
import coil3.disk.DiskCache
import coil3.disk.directory
import coil3.memory.MemoryCache
import coil3.network.okhttp.OkHttpNetworkFetcherFactory
import coil3.request.crossfade
import dagger.hilt.android.HiltAndroidApp
import org.maplibre.android.MapLibre

@HiltAndroidApp
class CropLyticsApp : Application(), SingletonImageLoader.Factory {
    override fun onCreate() {
        super.onCreate()
        // MapLibre needs no key: the satellite style uses Esri World Imagery raster tiles (CONTRACT.md).
        MapLibre.getInstance(this)
    }

    /** Satellite thumbnails are kept on disk so the field list still has pictures offline. */
    override fun newImageLoader(context: PlatformContext): ImageLoader = ImageLoader.Builder(context)
        .components { add(OkHttpNetworkFetcherFactory()) }
        .memoryCache { MemoryCache.Builder().maxSizePercent(context, 0.15).build() }
        .diskCache { DiskCache.Builder().directory(cacheDir.resolve("thumbs")).maxSizeBytes(40L * 1024 * 1024).build() }
        .crossfade(true)
        .build()
}
