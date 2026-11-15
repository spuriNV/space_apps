import Foundation

/// Names a field the way the grower does: "Rice field 4 miles east of Williams", "149 acres, rice in 2025, Colusa County".
/// Ported from frontend/app/src/components/ui/shared.tsx; the API's own `farmer_name` wins when it is sent.
enum FieldNaming {
    /// Cropland Data Layer labels -> what a grower says.
    static func cropName(_ raw: String?) -> String {
        guard var c = raw, !c.isEmpty else { return "Not recorded" }
        c = c.replacingOccurrences(of: " (CDL pending)", with: "")
        if c.hasPrefix("Fallow") { return "Left fallow" }
        if c.hasPrefix("Dbl Crop WinWht/Corn") { return "Wheat, then corn" }
        if c.hasPrefix("Dbl Crop ") { return c.replacingOccurrences(of: "Dbl Crop ", with: "").replacingOccurrences(of: "/", with: ", then ") }
        return c
    }

    static func sortedYears(_ history: [String: String]) -> [Int] {
        history.keys.compactMap(Int.init).sorted()
    }

    /// The crop the field is known for: the most frequent non-fallow crop over the last 10 years on record.
    static func mainCrop(_ history: [String: String]) -> String {
        var counts: [String: Int] = [:]
        var lastSeen: [String: Int] = [:]
        for y in sortedYears(history).suffix(10) {
            let c = cropName(history[String(y)])
            guard c != "Left fallow", c != "Not recorded" else { continue }
            counts[c, default: 0] += 1
            lastSeen[c] = y
        }
        let best = counts.max { a, b in a.value == b.value ? (lastSeen[a.key] ?? 0) < (lastSeen[b.key] ?? 0) : a.value < b.value }
        return best?.key ?? "Crop"
    }

    static func latestCrop(_ history: [String: String]) -> (year: Int, crop: String)? {
        guard let y = sortedYears(history).last else { return nil }
        return (y, cropName(history[String(y)]))
    }

    private static let towns: [(String, Double, Double)] = [
        ("Williams", 39.1546, -122.1494), ("Colusa", 39.2143, -122.0094), ("Arbuckle", 39.0174, -122.0578), ("Maxwell", 39.2763, -122.1914),
        ("Grimes", 39.0749, -121.8986), ("Glenn", 39.5213, -122.0130), ("Richvale", 39.4949, -121.7458), ("Biggs", 39.4124, -121.7128),
        ("Robbins", 38.8710, -121.7044), ("Zamora", 38.7963, -121.8816), ("Hanford", 36.3275, -119.6457), ("Lemoore", 36.3008, -119.7829),
        ("Corcoran", 36.0980, -119.5604), ("Stratford", 36.1897, -119.8232), ("Goshen", 36.3511, -119.4193), ("Tipton", 36.0594, -119.3120),
        ("Riverdale", 36.4311, -119.8596), ("El Nido", 37.1349, -120.4910), ("Newman", 37.3138, -121.0208),
    ]
    private static let directions = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]

    /// "3.5 miles east of Williams": the nearest town from a short list.
    static func nearTown(lat: Double, lon: Double, county: String) -> String {
        var best: (name: String, km: Double, dx: Double, dy: Double)?
        for (name, tlat, tlon) in towns {
            let dx = (lon - tlon) * 111.32 * cos(lat * .pi / 180)
            let dy = (lat - tlat) * 110.57
            let km = (dx * dx + dy * dy).squareRoot()
            if best == nil || km < best!.km { best = (name, km, dx, dy) }
        }
        guard let b = best, b.km <= 60 else { return "in \(county) County" }
        let miles = max(1, (b.km * 0.621 * 2).rounded() / 2)
        var angle = atan2(b.dx, b.dy) * 180 / .pi
        if angle < 0 { angle += 360 }
        let dir = directions[Int((angle / 45).rounded()) % 8]
        let milesText = miles.truncatingRemainder(dividingBy: 1) == 0 ? String(Int(miles)) : String(format: "%.1f", miles)
        return "\(milesText) mile\(miles == 1 ? "" : "s") \(dir) of \(b.name)"
    }

    private static let countyByFips: [String: String] = [
        "001": "Alameda", "007": "Butte", "011": "Colusa", "013": "Contra Costa", "017": "El Dorado", "019": "Fresno",
        "021": "Glenn", "025": "Imperial", "029": "Kern", "031": "Kings", "033": "Lake", "037": "Los Angeles", "039": "Madera",
        "047": "Merced", "053": "Monterey", "057": "Nevada", "061": "Placer", "065": "Riverside", "067": "Sacramento",
        "069": "San Benito", "071": "San Bernardino", "073": "San Diego", "077": "San Joaquin", "079": "San Luis Obispo",
        "083": "Santa Barbara", "089": "Shasta", "095": "Solano", "099": "Stanislaus", "101": "Sutter", "103": "Tehama",
        "107": "Tulare", "111": "Ventura", "113": "Yolo", "115": "Yuba",
    ]

    static func county(_ f: FieldLocation) -> String {
        if let n = f.countyName, !n.isEmpty { return n.replacingOccurrences(of: " County", with: "") }
        if let fips = f.countyFips, let n = countyByFips[String(fips.suffix(3))] { return n }
        return "California"
    }

    static func acres(_ f: FieldLocation) -> Int {
        if let a = f.acresValue { return Int(a.rounded()) }
        if let ha = f.areaHa?.value { return Int(Units.acres(fromHectares: ha).rounded()) }
        return 0
    }

    /// "Rice field 4 miles east of Williams".
    static func displayName(_ f: FieldLocation) -> String {
        if let n = f.farmerName, !n.isEmpty { return n }
        let crop = mainCrop(f.cropHistory).components(separatedBy: ",").first ?? "Crop"
        return "\(crop) field \(nearTown(lat: f.centroid.lat, lon: f.centroid.lon, county: county(f)))"
    }

    /// "Rice in 2025": this year's crop, or the latest year on record (the USDA map comes out the next spring).
    static func cropLine(_ f: FieldLocation) -> String {
        guard let latest = latestCrop(f.cropHistory) else { return "Crop not on record" }
        return latest.crop == "Left fallow" ? "Left fallow in \(latest.year)" : "\(latest.crop) in \(latest.year)"
    }

    /// "149 acres, rice in 2025, Colusa County".
    static func subtitle(_ f: FieldLocation) -> String {
        var parts = ["\(acres(f)) acres"]
        if let latest = latestCrop(f.cropHistory) {
            parts.append(latest.crop == "Left fallow" ? "left fallow in \(latest.year)" : "\(latest.crop.lowercased()) in \(latest.year)")
        }
        parts.append("\(county(f)) County")
        return parts.joined(separator: ", ")
    }

    /// "Rice in 8 of the last 10 years; left fallow 2016, 2020 and 2022."
    static func recordLine(_ f: FieldLocation) -> String {
        let years = Array(sortedYears(f.cropHistory).suffix(10))
        guard !years.isEmpty else { return "" }
        let main = mainCrop(f.cropHistory).components(separatedBy: ",").first ?? "Crop"
        let n = years.filter { cropName(f.cropHistory[String($0)]).hasPrefix(main) }.count
        let fallow = years.filter { cropName(f.cropHistory[String($0)]) == "Left fallow" }
        var line = "\(main) in \(n) of the last \(years.count) years"
        if !fallow.isEmpty { line += "; left fallow \(listText(fallow.map(String.init)))" }
        return line + "."
    }

    static func listText(_ items: [String]) -> String {
        guard items.count > 1 else { return items.first ?? "" }
        return items.dropLast().joined(separator: ", ") + " and " + items.last!
    }

    /// Engine rotation ids -> short names a grower would use.
    static func shortRotationName(_ s: Strategy) -> String {
        let known: [String: String] = [
            "car0_rice_winterflood": "Rice + winter flood", "car1_rice_wintercover": "Rice + winter cover",
            "car2_dryyear_safflower": "Dry-year safflower", "car3_rice_wheat": "Rice, then wheat",
            "caf0_alfalfa": "Alfalfa stand", "caf1_smallgrain_corn": "Small grain + corn",
            "caf2_smallgrain_sorghumsudan": "Small grain + sorghum-sudan", "caf3_alfalfa_break": "Short alfalfa + break",
        ]
        if let k = known[s.id] { return k }
        for (suffix, name) in known where s.id.hasSuffix(String(suffix.drop { $0 != "_" })) { return name }
        return s.name.components(separatedBy: CharacterSet(charactersIn: ",(")).first?.trimmingCharacters(in: .whitespaces) ?? s.name
    }
}
