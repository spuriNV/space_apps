package app.croplytics.data.local

import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.RoomDatabase
import androidx.room.Upsert

/**
 * One row per API response, stored as JSON. Keeps the last-seen data for every field so the
 * app opens offline and says "Saved on <date>". Keys look like `location/car_colusa_rice`.
 */
@Entity(tableName = "cached_response")
data class CachedResponseEntity(
    @PrimaryKey val key: String,
    val json: String,
    val savedAtEpochMs: Long,
)

@Dao
interface CacheDao {
    @Query("SELECT * FROM cached_response WHERE `key` = :key")
    suspend fun get(key: String): CachedResponseEntity?

    @Upsert
    suspend fun put(entity: CachedResponseEntity)
}

@Database(entities = [CachedResponseEntity::class], version = 1, exportSchema = true)
abstract class CacheDatabase : RoomDatabase() {
    abstract fun cacheDao(): CacheDao
}
