import SwiftUI

/// "Viewing": quick picks in the grower's words, then a month picker (the last 4 years; earlier on request).
struct DateSheet: View {
    @Environment(AppModel.self) private var app
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        @Bindable var app = app
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    VStack(spacing: 0) {
                        ForEach(QuickDates.picks(today: app.today), id: \.label) { q in
                            let on = app.t == q.t
                            Button {
                                app.stopReplay(); app.setDate(q.t); dismiss()
                            } label: {
                                HStack {
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(q.label).font(.clBodyStrong).foregroundStyle(on ? Palette.onAccentContainer : Palette.text)
                                        Text(q.sub).font(.clCite).foregroundStyle(Palette.muted)
                                    }
                                    Spacer()
                                    if on { Image(systemName: "checkmark").foregroundStyle(Palette.accentOutline) }
                                }
                                .padding(.horizontal, 12).frame(minHeight: 52)
                                .background(RoundedRectangle(cornerRadius: Radius.md, style: .continuous).fill(on ? Palette.accentContainer : .clear))
                                .contentShape(Rectangle())
                            }
                            .buttonStyle(StateLayerStyle(shape: RoundedRectangle(cornerRadius: Radius.md, style: .continuous)))
                            .accessibilityAddTraits(on ? .isSelected : [])
                            .accessibilityIdentifier("quick-\(q.label)")
                        }
                    }
                    ForEach(QuickDates.years(today: app.today, earlier: app.showEarlier), id: \.self) { y in
                        VStack(alignment: .leading, spacing: 6) {
                            Text(String(y)).font(.clLabel).foregroundStyle(Palette.text)
                            LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 6), count: 6), spacing: 6) {
                                ForEach(0..<12, id: \.self) { m in
                                    let t = TimePoint(year: y, dekad: m * 3 + 1)
                                    let future = t > app.today
                                    let on = app.t.year == y && app.t.month == m + 1
                                    Button(GrowerDate.months[m]) { app.stopReplay(); app.setDate(t); dismiss() }
                                        .font(.clLabel)
                                        .frame(maxWidth: .infinity, minHeight: 36)
                                        .foregroundStyle(on ? Palette.onAccentContainer : future ? Palette.muted : Palette.text2)
                                        .background(Capsule().fill(on ? Palette.accentContainer : Palette.panel2))
                                        .disabled(future)
                                        .opacity(future ? 0.5 : 1)
                                        .accessibilityLabel("\(GrowerDate.monthsFull[m]) \(y)")
                                }
                            }
                        }
                    }
                    HStack {
                        Button(app.showEarlier ? "Hide earlier years" : "Show earlier years (2016–\(String(app.today.year - 4)))") { app.showEarlier.toggle() }
                            .buttonStyle(.pill(.text, small: true))
                        Spacer()
                        if !app.isToday {
                            Button("Back to today") { app.backToToday(); dismiss() }.buttonStyle(.pill(.outline, small: true))
                        }
                    }
                }
                .padding(Metrics.gutter)
            }
            .background(Palette.paper)
            .navigationTitle("Viewing")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .topBarTrailing) { Button("Done") { dismiss() } } }
        }
        .accessibilityIdentifier("date-sheet")
    }
}

/// Map layers: field outlines, the NASA footprints around the open field, and BC reserve boundaries (context only).
struct LayersSheet: View {
    @Environment(AppModel.self) private var app
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List {
                Section {
                    ForEach(MapLayer.allCases.filter { $0 != .reserves || app.selectedField?.isBC == true }, id: \.self) { layer in
                        Toggle(isOn: Binding(get: { app.layers.contains(layer) }, set: { on in
                            if on { app.layers.insert(layer) } else { app.layers.remove(layer) }
                        })) {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(layer.title).font(.clBodyStrong)
                                Text(layer.tellsYou).font(.clCite).foregroundStyle(Palette.muted)
                            }
                        }
                        .tint(Palette.accent)
                        .listRowBackground(Palette.paper)
                    }
                } footer: {
                    Text("Footprints show around the open field. Imagery: Apple Maps satellite.").font(.clCite)
                }
            }
            .scrollContentBackground(.hidden)
            .background(Palette.paper)
            .navigationTitle("Map layers")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .topBarTrailing) { Button("Done") { dismiss() } } }
        }
    }
}

/// Every source, NASA first (web Sources.tsx); BC fields swap in Canadian ground data.
struct SourcesSheet: View {
    let bc: Bool
    @Environment(\.dismiss) private var dismiss

    static let groups: [(String, [(String, String)])] = [
        ("NASA", [
            ("HLS (Harmonized Landsat Sentinel-2), NASA/USGS", "Bare, green or flooded every few days; the field calendar. 100 ft squares."),
            ("Landsat 8 and 9, NASA/USGS", "Greenness since 2016, inside HLS and the 3D view."),
            ("GPM IMERG, NASA/JAXA", "Daily rain over the field; rain since 1 Oct and its 2001–2025 normal. 6-mile squares."),
            ("GRACE-FO data assimilation, NASA", "Groundwater and root-zone soil moisture percentiles, weekly; a 17-mile square. Groundwater is the whole basin, not your own well."),
            ("SMAP, NASA", "Root-zone soil moisture, one reading for a 6-mile square, when its readings are in."),
            ("OPERA surface water (DSWx), NASA JPL", "Standing water on the field in each clear image. 100 ft squares."),
            ("NASA POWER", "Sun, wind and humidity for crop water use (the rotation model)."),
            ("NASADEM, NASA JPL", "Slope and low spots. 100 ft squares."),
            ("Astronaut photography, NASA Johnson Space Center", "The ISS photo of the valley."),
        ]),
        ("Other satellites", [
            ("Sentinel-2, ESA (Copernicus)", "The 30 m grid in the 3D view; also inside HLS."),
            ("OpenET ensemble", "Measured crop water use on this field, monthly, 2016–2025; the check on the model."),
        ]),
        ("Ground data", [
            ("NOAA weather stations (GHCN-Daily)", "Hot days (104 °F), frost nights, heavy-rain days."),
            ("USDA Cropland Data Layer", "The crop grown each year, 2008–2025."),
            ("USDA soil survey (SSURGO)", "Soil type, sand, silt and clay (top 3 feet), water held, drainage, salt."),
            ("DWR / Land IQ crop mapping 2023", "The field outline and state field number."),
            ("USDA Risk Management Agency", "Crop-insurance payouts by county, crop and cause."),
            ("NOAA Climate Prediction Center, US Drought Monitor", "Winter outlooks and drought, county."),
            ("CDEC, Reclamation, DWR", "Reservoir storage, allocations, snowpack."),
        ]),
        ("Models", [
            ("CropLytics rotation model", "FAO-56 crop water use and rules of thumb for soil, feed and pests; weather 2015–2025."),
            ("Bare / green / flooded rule", "Greenness below 0.2 is bare, 0.2–0.35 thin; a water index for flooding."),
            ("Machine-learning calendar (random forest)", "A second opinion on the rule, trained on neighbouring fields; tested on 2022."),
            ("Crop-stress weeks", "Two statistical methods on greenness, heat and dry air, growing season only."),
        ]),
    ]
    static let bcGround: (String, [(String, String)]) = ("Ground data (British Columbia)", [
        ("Environment and Climate Change Canada daily climate", "Hot days, frost nights and station rain."),
        ("AAFC Annual Crop Inventory", "The crop grown each year, 2011–2025. One class for hay and pasture."),
        ("ParcelMap BC and the Agricultural Land Reserve", "The field outline: a farmland parcel clipped to forage pixels. No owner kept."),
        ("AAFC Soil Landscapes of Canada v3.2", "Soil texture, water held and drainage from a 1:1,000,000 map; not field scale."),
        ("BC Gov News, Water Sustainability Act orders", "The 2023 and 2026 orders to stop irrigating in the Salmon River watershed."),
        ("Indian reserves (CLSS boundaries), BC Data Catalogue", "Reserve outlines and distances, for context only."),
    ])

    var body: some View {
        let groups = bc ? Self.groups.filter { $0.0 != "Ground data" }.map { g in (g.0, g.1.filter { !$0.0.contains("OpenET") }) } + [Self.bcGround] : Self.groups
        NavigationStack {
            List {
                ForEach(groups, id: \.0) { g in
                    Section(g.0) {
                        ForEach(g.1, id: \.0) { item in
                            VStack(alignment: .leading, spacing: 3) {
                                Text(item.0).font(.clBodyStrong)
                                Text(item.1).font(.clSecondary).foregroundStyle(Palette.text2)
                            }
                            .listRowBackground(Palette.paper)
                        }
                    }
                }
            }
            .scrollContentBackground(.hidden)
            .background(Palette.paper)
            .navigationTitle("Sources")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .topBarTrailing) { Button("Done") { dismiss() } } }
        }
    }
}
