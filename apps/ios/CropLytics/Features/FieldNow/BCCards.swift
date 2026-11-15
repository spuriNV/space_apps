import SwiftUI

/// "Working with First Nations" (BC fields only, web FirstNations.tsx). Farmer default: the statement, whether the
/// field is on reserve land, and the Nation on the lower river. More detail: nearby reserves, how we would start,
/// principles, public contact pages, and the water and salmon timeline. Public facts and links only.
struct FirstNationsCard: View {
    let session: FieldSession
    @Environment(AppModel.self) private var app

    static func reserveName(_ s: String) -> String {
        s.lowercased().split(separator: " ", omittingEmptySubsequences: false).map { w -> String in
            guard let f = w.first else { return String(w) }
            if f == "(" , w.count > 1 { return "(" + w.dropFirst().prefix(1).uppercased() + w.dropFirst(2) }
            return f.uppercased() + w.dropFirst()
        }.joined(separator: " ")
    }

    var body: some View {
        let s = session.field.firstNations
        let fn = session.firstNations.value
        let statement = fn?.statement ?? s?.statement
        if statement != nil || fn != nil {
            VStack(alignment: .leading, spacing: 8) {
                SectionHeader("Working with First Nations")
                if let statement { Text(statement).font(.clBody).foregroundStyle(Palette.text).fixedSize(horizontal: false, vertical: true) }
                let onReserve = fn?.fieldOnReserve ?? s?.fieldOnReserve ?? false
                let km = fn?.nearestKm ?? s?.nearestKm
                let nation = fn?.nearestNation ?? s?.nearestNation
                bullet(onReserve ? "This field is on reserve land." : "This field is not on reserve land\(km.map { "; nearest reserve \(Units.oneDecimal($0)) km" } ?? "")\(nation.map { " (\($0))" } ?? "").")
                let river = session.field.waterContext?.watershed?.components(separatedBy: CharacterSet(charactersIn: "(;,")).first?.trimmingCharacters(in: .whitespaces) ?? "river"
                if let lower = fn?.lowerRiver?.nation ?? s?.lowerRiverNation {
                    HStack(alignment: .firstTextBaseline, spacing: 4) {
                        bullet("Nation on the lower \(river): \(lower).")
                        if let u = fn?.lowerRiver?.url, let url = URL(string: u) { Link("Lands page", destination: url).font(.clSecondary) }
                    }
                }
                if app.detailOn { detail(fn) }
            }
            .accessibilityIdentifier("first-nations")
        }
    }

    private func bullet(_ t: String) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 8) {
            Circle().fill(Palette.muted).frame(width: 4, height: 4).offset(y: -3)
            Text(t).font(.clBody).foregroundStyle(Palette.text2).fixedSize(horizontal: false, vertical: true)
        }
    }

    @ViewBuilder private func detail(_ fn: FirstNationsDetail?) -> some View {
        if let fn {
            VStack(alignment: .leading, spacing: 6) {
                Text("Reserves near this field").font(.clLabel).padding(.top, 8)
                ForEach(fn.nearby.filter { $0.distanceKm <= 20 }.sorted { $0.distanceKm < $1.distanceKm }) { r in
                    FactRow(label: "\(Units.oneDecimal(r.distanceKm)) km", value: Self.reserveName(r.reserve), note: r.nation)
                }
                if !fn.engagementSteps.isEmpty {
                    Text("How we would start").font(.clLabel).padding(.top, 8)
                    ForEach(Array(fn.engagementSteps.enumerated()), id: \.offset) { i, x in
                        Text("\(i + 1). \(x)").font(.clSecondary).foregroundStyle(Palette.text2).fixedSize(horizontal: false, vertical: true)
                    }
                }
                if !fn.principles.isEmpty {
                    Text("Principles we follow").font(.clLabel).padding(.top, 8)
                    ForEach(fn.principles) { p in
                        VStack(alignment: .leading, spacing: 2) {
                            if let u = p.url, let url = URL(string: u) { Link(p.name, destination: url).font(.clBodyStrong) } else { Text(p.name).font(.clBodyStrong) }
                            if let d = p.description { Text(d).font(.clSecondary).foregroundStyle(Palette.text2).fixedSize(horizontal: false, vertical: true) }
                        }
                    }
                }
                if !fn.contacts.isEmpty {
                    Text("Public contact pages").font(.clLabel).padding(.top, 8)
                    ForEach(fn.contacts, id: \.nation) { c in
                        HStack(alignment: .firstTextBaseline) {
                            if let u = c.url, let url = URL(string: u) { Link(c.nation, destination: url).font(.clBodyStrong) } else { Text(c.nation).font(.clBodyStrong) }
                            if let d = c.department { Text(d).font(.clSecondary).foregroundStyle(Palette.muted) }
                        }
                    }
                }
                if !fn.waterTimeline.isEmpty {
                    Text("Water and salmon").font(.clLabel).padding(.top, 8)
                    ForEach(fn.waterTimeline, id: \.title) { x in
                        FactRow(label: GrowerDate.short(x.date) ?? x.date, value: x.title)
                    }
                }
                SourceLine(text: "BC Data Catalogue and the Nations' own public pages." + (fn.notes.dropFirst().first.map { " \($0)" } ?? ""))
            }
            .accessibilityIdentifier("first-nations-detail")
        } else if session.firstNations.isLoading {
            ProgressView()
        } else {
            Text("More on the Nations is not available right now.").font(.clSecondary).italic().foregroundStyle(Palette.muted)
        }
    }
}

/// Salmon in the river beside a BC field: shown only once GET .../salmon is published (it answers 404 today).
struct SalmonPanel: View {
    let session: FieldSession
    var body: some View {
        if let s = session.salmon.value, !s.isEmpty {
            VStack(alignment: .leading, spacing: 8) {
                SectionHeader(s.title ?? "Salmon in the river").padding(.top, Metrics.sectionGap)
                if let sum = s.summary { Text(sum).font(.clBody).foregroundStyle(Palette.text).fixedSize(horizontal: false, vertical: true) }
                ForEach(s.lines, id: \.self) { l in Text(l).font(.clSecondary).foregroundStyle(Palette.text2).fixedSize(horizontal: false, vertical: true) }
                ForEach(s.items) { i in
                    FactRow(label: i.date.flatMap { GrowerDate.short($0) } ?? "", value: i.title)
                }
                SourceLine(text: "Fisheries and Oceans Canada and BC records, via the CropLytics API.")
            }
            .accessibilityIdentifier("salmon-panel")
        }
    }
}
