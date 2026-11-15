package app.croplytics.data.local

import java.io.File

/**
 * Cache rows kept as files: the daily record and the 30 m grid are too big for one SQLite row
 * (Android's 2 MB CursorWindow), so they are stored next to the Room cache with the same contract.
 */
class FileStore(private val dir: File) : CacheDao {
    private fun file(key: String) = File(dir, key.replace(Regex("[^A-Za-z0-9._-]"), "_") + ".json")

    override suspend fun get(key: String): CachedResponseEntity? {
        val f = file(key)
        return if (f.isFile) CachedResponseEntity(key, f.readText(), f.lastModified()) else null
    }

    override suspend fun put(entity: CachedResponseEntity) {
        dir.mkdirs()
        val f = file(entity.key)
        val tmp = File(dir, f.name + ".tmp")
        tmp.writeText(entity.json)
        tmp.renameTo(f)
        f.setLastModified(entity.savedAtEpochMs)
    }
}
