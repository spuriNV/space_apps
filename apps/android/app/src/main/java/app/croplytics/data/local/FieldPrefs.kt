package app.croplytics.data.local

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.doublePreferencesKey
import androidx.datastore.preferences.core.edit
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

/** The grower's own settings: one water limit (acre-feet per acre a year) per field. */
interface FieldPrefs {
    fun waterLimit(fieldId: String): Flow<Double?>
    suspend fun setWaterLimit(fieldId: String, acreFeetPerAcre: Double)
}

@Singleton
class DataStoreFieldPrefs @Inject constructor(
    private val store: DataStore<Preferences>,
) : FieldPrefs {
    private fun key(id: String) = doublePreferencesKey("water_limit_$id")

    override fun waterLimit(fieldId: String): Flow<Double?> = store.data.map { it[key(fieldId)] }

    override suspend fun setWaterLimit(fieldId: String, acreFeetPerAcre: Double) {
        store.edit { it[key(fieldId)] = acreFeetPerAcre }
    }
}
