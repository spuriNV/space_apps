# kotlinx.serialization: keep generated serializers for the API DTOs.
-keepattributes *Annotation*, InnerClasses, Signature, Exceptions
-keepclassmembers @kotlinx.serialization.Serializable class app.croplytics.** {
    *** Companion;
    *** INSTANCE;
    kotlinx.serialization.KSerializer serializer(...);
}
-keep,includedescriptorclasses class app.croplytics.**$$serializer { *; }
# Retrofit service interfaces are used through reflection.
-keep,allowobfuscation interface app.croplytics.data.remote.CropLyticsApi
-keep,allowobfuscation,allowshrinking class kotlin.coroutines.Continuation
-dontwarn org.slf4j.**
# MapLibre ships its own consumer rules; keep JNI-bound classes.
-keep class org.maplibre.** { *; }
