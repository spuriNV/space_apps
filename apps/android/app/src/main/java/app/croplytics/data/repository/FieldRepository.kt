package app.croplytics.data.repository

import app.croplytics.data.remote.dto.CalendarDto
import app.croplytics.data.remote.dto.GlossaryDto
import app.croplytics.data.remote.dto.InsuranceDto
import app.croplytics.data.remote.dto.LocationDto
import app.croplytics.data.remote.dto.ModelsDto
import app.croplytics.data.remote.dto.NasaNowDto
import app.croplytics.data.remote.dto.OpenEtDto
import app.croplytics.data.remote.dto.OutlookDto
import app.croplytics.data.remote.dto.StrategyDto
import app.croplytics.data.remote.dto.StressDto
import app.croplytics.data.remote.dto.WaterSeenDto
import kotlinx.coroutines.flow.Flow

/**
 * Single source of truth for field data. Every call is offline-first: the copy saved on the phone
 * comes first (if any), then the server's answer replaces it. Pass `force = true` to skip the
 * "fresh enough" shortcut (pull to refresh, "Try again").
 */
interface FieldRepository {
    fun locations(force: Boolean = false): Flow<LoadState<List<LocationDto>>>
    fun location(id: String, force: Boolean = false): Flow<LoadState<LocationDto>>
    fun calendar(id: String, force: Boolean = false): Flow<LoadState<CalendarDto>>
    fun nasaNow(id: String, force: Boolean = false): Flow<LoadState<NasaNowDto>>
    fun strategies(id: String, force: Boolean = false): Flow<LoadState<List<StrategyDto>>>
    fun outlook(id: String, force: Boolean = false): Flow<LoadState<OutlookDto>>
    fun models(id: String, force: Boolean = false): Flow<LoadState<ModelsDto>>
    fun openet(id: String, force: Boolean = false): Flow<LoadState<OpenEtDto>>
    fun waterSeen(id: String, force: Boolean = false): Flow<LoadState<WaterSeenDto>>
    fun stress(id: String, force: Boolean = false): Flow<LoadState<StressDto>>
    fun insurance(id: String, force: Boolean = false): Flow<LoadState<InsuranceDto>>
    fun glossary(force: Boolean = false): Flow<LoadState<GlossaryDto>>

    /** Re-scores the rotations against a water limit (POST /score). Cached per limit. */
    fun score(id: String, limitAfAc: Double): Flow<LoadState<List<StrategyDto>>>

    /** The grower's water limit for this field, or null if they have not set one. */
    fun waterLimit(id: String): Flow<Double?>
    suspend fun setWaterLimit(id: String, acreFeetPerAcre: Double)
}
