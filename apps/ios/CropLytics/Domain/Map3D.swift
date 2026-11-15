import Foundation

/// The "under the field" 3D stack and the satellite footprints, ported from Android `domain/Map3D.kt`
/// (itself from the web's MapView.tsx). Pure geometry and words: the map draws them. Heights are metres above
/// ground and rise with zoom between `z0` and `z1` (style expressions, not camera writes).
enum Map3D {
    static let z0 = 12.5
    static let z1 = 14.2
    /// The stack reads as 3D past this zoom with a field open (the "drilled" flag).
    static let drilledZoom = 13.4
    static let homeLat = 37.35, homeLon = -119.9, homeZoom = 5.75
    static let maxPitch = 58.0, maxBearing = -22.0

    /// 0 before the slabs leave the ground (a little before `z0`, so the tilt leads), 1 at `z1`.
    static func zoomFraction(_ zoom: Double) -> Double {
        min(1, max(0, (zoom - (z0 - 0.3)) / (z1 - z0)))
    }
    static func pitch(forFraction f: Double) -> Double { f * maxPitch }
    static func bearing(forFraction f: Double) -> Double { f > 0 ? maxBearing * f : 0 }
    static func isDrilled(zoom: Double, fieldOpen: Bool) -> Bool { fieldOpen && zoom > drilledZoom }

    /// A prism in lon/lat with a base and top in metres above ground.
    struct Extrusion: Equatable {
        let ring: [[Double]]   // [lon, lat], closed
        let base: Double
        let height: Double
        let color: String
    }

    struct Stack {
        let cells: [Extrusion]
        let smap: [Extrusion]
        let grace: [Extrusion]
        let posts: [Extrusion]
        let shadow: [[[Double]]]
        let soilWords: String
        let groundwaterWords: String
    }

    struct Box: Equatable { let w: Double, s: Double, e: Double, n: Double }

    static func bbox(_ rings: [[(lon: Double, lat: Double)]]) -> Box? {
        let pts = rings.flatMap { $0 }
        guard let f = pts.first else { return nil }
        var b = Box(w: f.lon, s: f.lat, e: f.lon, n: f.lat)
        for p in pts { b = Box(w: min(b.w, p.lon), s: min(b.s, p.lat), e: max(b.e, p.lon), n: max(b.n, p.lat)) }
        return b
    }
    static let mPerDegLat = 111_320.0
    static func mPerDegLon(_ lat: Double) -> Double { 111_320.0 * cos(lat * .pi / 180) }
    static func rect(_ w: Double, _ s: Double, _ e: Double, _ n: Double) -> [[Double]] { [[w, s], [e, s], [e, n], [w, n], [w, s]] }
    static func padded(_ b: Box, lat: Double, padM: Double) -> [[Double]] {
        rect(b.w - padM / mPerDegLon(lat), b.s - padM / mPerDegLat, b.e + padM / mPerDegLon(lat), b.n + padM / mPerDegLat)
    }

    // MARK: Cells

    /// "2025_q3" key for a viewing date (year, month 1...12).
    static func quarterKey(year: Int, month: Int) -> String { "\(year)_q\((month - 1) / 3 + 1)" }

    /// The quarter's greenness, or the latest earlier quarter that has one (up to two years back).
    static func ndvi(_ byQuarter: [String: Double], year: Int, month: Int) -> Double? {
        var y = year, q = (month - 1) / 3 + 1
        for _ in 0..<8 {
            if let v = byQuarter["\(y)_q\(q)"] { return v }
            q -= 1; if q == 0 { q = 4; y -= 1 }
        }
        return nil
    }

    /// Cover colour: bare soil brown, thin cover light green, a crop green, no clear view grey.
    static func cellColor(_ ndvi: Double?) -> String {
        guard let v = ndvi else { return "#9A9C94" }
        return v < 0.2 ? "#A8703F" : v < 0.35 ? "#B7D77A" : "#2F9E4B"
    }

    static func cellHeight(ndvi: Double?, scale s: Double) -> (base: Double, top: Double) {
        let base = 430 * s
        let h = max(0, min(1, ndvi ?? 0))
        return (base, base + (8 + h * 175) * s)
    }

    /// Slab thickness rises a little with the percentile.
    static func slabThickness(pct: Double?, fallback: Double, scale s: Double) -> Double { (14 + (pct ?? fallback) * 0.42) * s }

    // MARK: Words

    static func band(_ v: Double, hi: String, mid: String, lo: String) -> String { v >= 67 ? hi : v > 33 ? mid : lo }
    static func soilWords(_ pct: Double?) -> String {
        pct.map { "\(band($0, hi: "Wetter than usual", mid: "About normal", lo: "Drier than usual")) (\(Units.ordinal(Int($0.rounded()))) percentile)" } ?? "No reading"
    }
    static func groundwaterWords(_ pct: Double?) -> String {
        pct.map { "\(band($0, hi: "More than usual", mid: "About normal", lo: "Less than usual")) (\(Units.ordinal(Int($0.rounded()))) percentile)" } ?? "No reading: gap between satellite missions"
    }

    /// Miles on a side of a square `degrees` wide (the satellite footprints), for "this 6-mile square".
    static func footprintMiles(degrees: Double) -> Int { Int((degrees * mPerDegLat / 1609.0).rounded()) }
    static func footprintLabel(word: String, degrees: Double) -> String { "\(word): this \(footprintMiles(degrees: degrees))-mile square" }

    /// Slab colours: light to dark by percentile (darker = wetter than usual). Blue family soil, pink family groundwater.
    static func smapColor(_ pct: Double?) -> String { pct.map { ramp($0, from: (0xCF, 0xE6, 0xFF), to: (0x1F, 0x5F, 0xBF)) } ?? "#737A86" }
    static func graceColor(_ pct: Double?) -> String { pct.map { ramp($0, from: (0xFF, 0xD3, 0xE6), to: (0xC2, 0x1B, 0x6B)) } ?? "#5D636E" }
    private static func ramp(_ pct: Double, from a: (Int, Int, Int), to b: (Int, Int, Int)) -> String {
        let t = max(0, min(1, pct / 100))
        func mix(_ x: Int, _ y: Int) -> Int { Int((Double(x) + (Double(y) - Double(x)) * t).rounded()) }
        return String(format: "#%02X%02X%02X", mix(a.0, b.0), mix(a.1, b.1), mix(a.2, b.2))
    }

    // MARK: Stack

    /// Bottom to top: groundwater slab (wide pad), soil-moisture slab (tighter pad), the 30 m cover cells.
    static func stack(rings: [[(lon: Double, lat: Double)]], lat: Double,
                      cells: [(ring: [(lon: Double, lat: Double)], ndvi: Double?)],
                      soilPct: Double?, groundwaterPct: Double?) -> Stack? {
        guard let b = bbox(rings) else { return nil }
        let extentM = max((b.e - b.w) * mPerDegLon(lat), (b.n - b.s) * mPerDegLat)
        let s = max(0.3, min(4, extentM / 990))
        let cellExt = cells.map { c -> Extrusion in
            let (base, top) = cellHeight(ndvi: c.ndvi, scale: s)
            return Extrusion(ring: closed(c.ring), base: base, height: top, color: cellColor(c.ndvi))
        }
        let sBase = 235 * s, gBase = 45 * s
        let smap = [Extrusion(ring: padded(b, lat: lat, padM: 110 * s), base: sBase, height: sBase + slabThickness(pct: soilPct, fallback: 10, scale: s), color: smapColor(soilPct))]
        let grace = [Extrusion(ring: padded(b, lat: lat, padM: 230 * s), base: gBase, height: gBase + slabThickness(pct: groundwaterPct, fallback: 4, scale: s), color: graceColor(groundwaterPct))]
        let pw = 5 * s
        let posts = [(b.w, b.s), (b.e, b.s), (b.e, b.n), (b.w, b.n)].map { x, y in
            Extrusion(ring: rect(x - pw / mPerDegLon(lat), y - pw / mPerDegLat, x + pw / mPerDegLon(lat), y + pw / mPerDegLat), base: 0, height: 430 * s, color: "#E8EEF7")
        }
        return Stack(cells: cellExt, smap: smap, grace: grace, posts: posts, shadow: [padded(b, lat: lat, padM: 230 * s)],
                     soilWords: soilWords(soilPct), groundwaterWords: groundwaterWords(groundwaterPct))
    }

    private static func closed(_ r: [(lon: Double, lat: Double)]) -> [[Double]] {
        var out = r.map { [$0.lon, $0.lat] }
        if let f = out.first, out.last != f { out.append(f) }
        return out
    }
}
