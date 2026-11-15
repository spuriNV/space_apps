package app.croplytics.ui.now

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import app.croplytics.data.remote.dto.FieldEventDto
import app.croplytics.data.remote.dto.GlossaryItemDto
import app.croplytics.data.remote.dto.LocationDto
import app.croplytics.data.remote.dto.NasaDatasetDto
import app.croplytics.data.repository.FieldRepository
import app.croplytics.data.repository.LoadError
import app.croplytics.data.repository.LoadState
import app.croplytics.data.repository.dataOrNull
import app.croplytics.domain.DetailBuilder
import app.croplytics.domain.FieldIdentity
import app.croplytics.domain.FieldNames
import app.croplytics.domain.FieldNowBuilder
import app.croplytics.domain.FieldNowSummary
import app.croplytics.domain.Rings
import app.croplytics.domain.WaterLimit
import app.croplytics.ui.common.DetailPart
import app.croplytics.ui.common.combinedStatus
import app.croplytics.ui.common.fieldId
import app.croplytics.ui.common.toDetail
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import java.time.Clock
import java.time.Instant
import java.time.LocalDate
import javax.inject.Inject

data class FieldDetail(
    val about: List<Pair<String, String>> = emptyList(),
    val crops: List<Pair<Int, String>> = emptyList(),
    val events: List<FieldEventDto> = emptyList(),
    val datasets: List<NasaDatasetDto> = emptyList(),
    val stress: DetailPart = DetailPart.Loading,
    val water: DetailPart = DetailPart.Loading,
    val machineLearning: DetailPart = DetailPart.Loading,
    val openet: DetailPart = DetailPart.Loading,
    val insurance: DetailPart = DetailPart.Loading,
    val sources: List<Pair<String, String?>> = emptyList(),
)

data class FieldNowUiState(
    val loading: Boolean = true,
    val waking: Boolean = false,
    val error: LoadError? = null,
    val offlineSavedAt: Instant? = null,
    val identity: FieldIdentity? = null,
    val rings: Rings = emptyList(),
    val summary: FieldNowSummary? = null,
    /** Parts of the summary still on their way (skeletons) or not available (words). */
    val partsLoading: Boolean = true,
    val calendarMissing: Boolean = false,
    val readingsMissing: Boolean = false,
    val rotationMissing: Boolean = false,
    val today: LocalDate = LocalDate.now(),
    val detail: FieldDetail = FieldDetail(),
    val glossary: List<GlossaryItemDto> = emptyList(),
)

@OptIn(ExperimentalCoroutinesApi::class)
@HiltViewModel
class FieldNowViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    private val repository: FieldRepository,
    private val clock: Clock,
) : ViewModel() {
    val fieldId = savedStateHandle.fieldId()
    private val reload = MutableStateFlow(0)

    private fun <T> load(f: (Boolean) -> Flow<LoadState<T>>) = reload.flatMapLatest { f(it > 0) }

    private val main = combine(
        load { repository.location(fieldId, it) },
        load { repository.calendar(fieldId, it) },
        load { repository.nasaNow(fieldId, it) },
        load { repository.strategies(fieldId, it) },
        repository.waterLimit(fieldId),
    ) { loc, cal, now, strat, saved -> Main(loc, cal, now, strat, saved) }

    private val extra = combine(
        listOf(
            load { repository.stress(fieldId, it) }, load { repository.waterSeen(fieldId, it) },
            load { repository.models(fieldId, it) }, load { repository.openet(fieldId, it) },
            load { repository.insurance(fieldId, it) }, load { repository.glossary(it) },
        ),
    ) { it.toList() }

    val state: StateFlow<FieldNowUiState> = combine(main, extra) { m, x -> reduce(m, x) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), FieldNowUiState(today = LocalDate.now(clock)))

    fun retry() = reload.update { it + 1 }

    private data class Main(
        val loc: LoadState<LocationDto>,
        val cal: LoadState<app.croplytics.data.remote.dto.CalendarDto>,
        val now: LoadState<app.croplytics.data.remote.dto.NasaNowDto>,
        val strat: LoadState<List<app.croplytics.data.remote.dto.StrategyDto>>,
        val savedLimit: Double?,
    )

    @Suppress("UNCHECKED_CAST")
    private fun reduce(m: Main, x: List<LoadState<*>>): FieldNowUiState {
        val today = LocalDate.now(clock)
        val status = combinedStatus(m.loc, m.cal, m.now, m.strat)
        val loc = m.loc.dataOrNull
        if (loc == null) {
            return FieldNowUiState(
                loading = m.loc !is LoadState.Failed,
                waking = status.waking,
                error = (m.loc as? LoadState.Failed)?.error,
                today = today,
            )
        }
        val limit = m.savedLimit ?: WaterLimit.example(loc, fieldId)
        val strategies = m.strat.dataOrNull
        val summary = FieldNowBuilder.build(loc, m.cal.dataOrNull, m.now.dataOrNull, strategies, limit, m.savedLimit == null, today)
        val stress = x[0] as LoadState<app.croplytics.data.remote.dto.StressDto>
        val water = x[1] as LoadState<app.croplytics.data.remote.dto.WaterSeenDto>
        val models = x[2] as LoadState<app.croplytics.data.remote.dto.ModelsDto>
        val openet = x[3] as LoadState<app.croplytics.data.remote.dto.OpenEtDto>
        val insurance = x[4] as LoadState<app.croplytics.data.remote.dto.InsuranceDto>
        val glossary = (x[5] as LoadState<app.croplytics.data.remote.dto.GlossaryDto>).dataOrNull?.items.orEmpty()
        val baseline = strategies?.firstOrNull { it.isBaseline }
        val sources = buildList {
            m.now.dataOrNull?.sources?.values?.forEach { s -> s.title?.let { add(it to s.url) } }
            m.cal.dataOrNull?.sources?.forEach { s -> s.title?.let { add(it to s.url) } }
            add("NASA POWER daily weather" to "https://power.larc.nasa.gov/")
            add("USDA NASS Cropland Data Layer" to "https://www.nass.usda.gov/Research_and_Science/Cropland/SARS1a.php")
            add("USDA NRCS soil survey (SSURGO)" to "https://sdmdataaccess.sc.egov.usda.gov/")
        }.distinctBy { it.first }
            .sortedByDescending { it.first.contains("NASA") } // NASA first
        return FieldNowUiState(
            loading = false,
            waking = status.waking,
            offlineSavedAt = status.offlineSavedAt,
            identity = FieldNames.identity(loc),
            rings = loc.geometry?.rings().orEmpty(),
            summary = summary,
            partsLoading = listOf(m.cal, m.now, m.strat).any { it is LoadState.Loading || it is LoadState.Waking },
            calendarMissing = m.cal is LoadState.Failed,
            readingsMissing = m.now is LoadState.Failed,
            rotationMissing = m.strat is LoadState.Failed,
            today = today,
            detail = FieldDetail(
                about = DetailBuilder.about(loc),
                crops = DetailBuilder.crops(loc),
                events = loc.events,
                datasets = loc.nasaDatasets,
                stress = stress.toDetail(DetailBuilder::stress),
                water = water.toDetail(DetailBuilder::water),
                machineLearning = models.toDetail(DetailBuilder::machineLearning),
                openet = openet.toDetail { DetailBuilder.openet(it, baseline) },
                insurance = insurance.toDetail(DetailBuilder::insurance),
                sources = sources,
            ),
            glossary = glossary,
        )
    }
}
