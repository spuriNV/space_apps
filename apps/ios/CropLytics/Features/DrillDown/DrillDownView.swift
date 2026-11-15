import SwiftUI
import SceneKit

/// "Under the field": the field's 30 m grid in 3D (SceneKit). Each 100 ft square rises with its greenness for the
/// quarter of the viewing date and takes its cover colour; under the field, a soil-moisture slab and a groundwater
/// slab, shaded by their percentiles. MapKit can't extrude polygons, and RealityKit's RealityView needs iOS 18 on
/// iPhone, so SceneKit draws it. Drag to turn, pinch to zoom.
struct DrillDownView: View {
    let session: FieldSession
    @Environment(AppModel.self) private var app
    @Environment(\.dismiss) private var dismiss
    @Environment(\.accessibilityReduceMotion) private var reduce
    @State private var scene: SCNScene?

    var body: some View {
        ZStack(alignment: .top) {
            Color(hex: 0x10130E).ignoresSafeArea()
            if let scene {
                SceneView(scene: scene, pointOfView: scene.rootNode.childNode(withName: "camera", recursively: false),
                          options: [.allowsCameraControl])
                    .ignoresSafeArea()
                    .accessibilityLabel(GridScene.describe(session: session, t: app.t))
            } else if let e = session.grid.error {
                VStack { Spacer(); ErrorStateView(error: e) { Task { await session.loadGrid() } }.background(Palette.paper); Spacer() }
            } else {
                ProgressView("Loading the 100 ft grid").tint(.white).foregroundStyle(.white).frame(maxHeight: .infinity)
            }
            VStack(spacing: 8) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Under the field").font(.clHeading).foregroundStyle(Palette.text)
                        Text(FieldNaming.displayName(session.field)).font(.clSecondary).foregroundStyle(Palette.text2)
                        Text("Greenness, \(GridScene.quarterLabel(app.t))").font(.clCite).foregroundStyle(Palette.muted)
                    }
                    Spacer()
                    IconButton(systemName: "xmark", label: "Close") { dismiss() }.accessibilityIdentifier("close-3d")
                }
                HStack(spacing: 8) {
                    Button { app.stopReplay(); app.setDate(app.t.advanced(by: -9)) } label: { Label("Earlier", systemImage: "chevron.left") }
                        .buttonStyle(.pill(.outline, small: true))
                    Button { app.stopReplay(); app.setDate(app.t.advanced(by: 9)) } label: { Label("Later", systemImage: "chevron.right") }
                        .buttonStyle(.pill(.outline, small: true)).disabled(app.isToday)
                    Spacer()
                }
            }
            .padding(14)
            .background(RoundedRectangle(cornerRadius: Radius.lg, style: .continuous).fill(Palette.paper))
            .elevation2()
            .padding(.horizontal, 12)

            VStack {
                Spacer()
                legend
            }
        }
        .task { await session.loadGrid() }
        .task(id: "\(session.grid.value?.cells.count ?? 0)-\(GridScene.quarterKey(app.t))") {
            guard let grid = session.grid.value else { return }
            scene = GridScene.make(grid: grid, t: app.t, soil: soilPct, groundwater: gwPct, animate: !reduce)
        }
    }

    private var soilPct: Double? {
        if let r = session.nasaNow.value?.reading("smap_rootzone_pct")?.value ?? session.nasaNow.value?.reading("grace_rootzone_pct")?.value, app.isToday { return r }
        return session.daily.value.flatMap { DailyAnalysis.readings($0, at: app.t).soil?.0 }
    }
    private var gwPct: Double? {
        if app.isToday, let r = session.nasaNow.value?.reading("grace_gw_pct")?.value { return r }
        return session.daily.value.flatMap { DailyAnalysis.readings($0, at: app.t).groundwater?.0 }
    }

    private var legend: some View {
        VStack(alignment: .leading, spacing: 6) {
            FlowLayout(spacing: 10) {
                ForEach([(CoverClass.bare, "Bare"), (.partial, "Thin"), (.covered, "Crop")], id: \.1) { c, t in
                    HStack(spacing: 4) { RoundedRectangle(cornerRadius: 2).fill(SeasonStripView.color(c)).frame(width: 10, height: 10); Text(t).font(.clCite) }
                }
                Text("Taller = greener").font(.clCite).foregroundStyle(Palette.muted)
            }
            Text("Under the field: soil moisture (brown, \(soilPct.map { Units.ordinal(Int($0.rounded())) + " percentile" } ?? "no reading")), then groundwater (blue, \(gwPct.map { Units.ordinal(Int($0.rounded())) + " percentile" } ?? "no reading"), whole basin). Darker = wetter than usual.")
                .font(.clCite).foregroundStyle(Palette.text2).fixedSize(horizontal: false, vertical: true)
            SourceLine(text: "Sentinel-2 and Landsat greenness, quarterly median per 100 ft square; NASA SMAP and GRACE-FO under the field.")
        }
        .foregroundStyle(Palette.text)
        .padding(14)
        .background(RoundedRectangle(cornerRadius: Radius.lg, style: .continuous).fill(Palette.paper))
        .elevation2()
        .padding(12)
    }
}

/// Builds the SceneKit scene from the 30 m grid.
@MainActor
enum GridScene {
    static func quarterKey(_ t: TimePoint) -> String { "\(t.year)_q\((t.month - 1) / 3 + 1)" }

    static func quarterLabel(_ t: TimePoint) -> String {
        let q = (t.month - 1) / 3
        return ["Jan–Mar", "Apr–Jun", "Jul–Sep", "Oct–Dec"][q] + " \(t.year)"
    }

    /// The quarter's greenness for a cell, or the latest earlier quarter that has one.
    static func ndvi(_ cell: FieldGrid.Cell, _ t: TimePoint) -> Double? {
        var y = t.year, q = (t.month - 1) / 3 + 1
        for _ in 0..<8 {
            if let v = cell.ndvi["\(y)_q\(q)"] { return v }
            q -= 1; if q == 0 { q = 4; y -= 1 }
        }
        return nil
    }

    static func describe(session: FieldSession, t: TimePoint) -> String {
        guard let cells = session.grid.value?.cells, !cells.isEmpty else { return "3D view of the field, loading" }
        let v = cells.compactMap { ndvi($0, t) }
        let bare = v.filter { $0 < 0.2 }.count, crop = v.filter { $0 >= 0.35 }.count
        return "3D view of \(cells.count) squares of 100 feet, \(quarterLabel(t)): \(crop) green, \(bare) bare, the rest thin."
    }

    static func uiColor(_ ndvi: Double?) -> UIColor {
        guard let v = ndvi else { return UIColor(hex: 0x9A9C94) }
        return v < 0.2 ? UIColor(hex: 0xA8703F) : v < 0.35 ? UIColor(hex: 0xB7D77A) : UIColor(hex: 0x2F9E4B)
    }

    static func make(grid: FieldGrid, t: TimePoint, soil: Double?, groundwater: Double?, animate: Bool) -> SCNScene {
        let scene = SCNScene()
        scene.background.contents = UIColor(hex: 0x10130E)
        let cells = grid.cells.filter { $0.inField >= 0.5 }
        let all = cells.flatMap(\.ring)
        let lat0 = all.map(\.latitude).reduce(0, +) / Double(max(all.count, 1))
        let lon0 = all.map(\.longitude).reduce(0, +) / Double(max(all.count, 1))
        let mx = 111_320 * cos(lat0 * .pi / 180), my = 110_540.0
        func local(_ lat: Double, _ lon: Double) -> (Float, Float) { (Float((lon - lon0) * mx), Float(-(lat - lat0) * my)) }

        let field = SCNNode()
        var minX: Float = 0, maxX: Float = 0, minZ: Float = 0, maxZ: Float = 0
        for c in cells {
            let lat = c.ring.map(\.latitude).reduce(0, +) / Double(c.ring.count)
            let lon = c.ring.map(\.longitude).reduce(0, +) / Double(c.ring.count)
            let (x, z) = local(lat, lon)
            minX = min(minX, x); maxX = max(maxX, x); minZ = min(minZ, z); maxZ = max(maxZ, z)
            let v = ndvi(c, t)
            let h = CGFloat(3 + max(0, min(1, v ?? 0)) * 70)
            let box = SCNBox(width: 27, height: h, length: 27, chamferRadius: 0)
            let m = SCNMaterial()
            m.diffuse.contents = uiColor(v)
            m.lightingModel = .lambert
            box.materials = [m]
            let n = SCNNode(geometry: box)
            n.position = SCNVector3(x, Float(h) / 2, z)
            field.addChildNode(n)
        }
        scene.rootNode.addChildNode(field.flattenedClone())

        let w = CGFloat(maxX - minX + 60), l = CGFloat(maxZ - minZ + 60)
        let cx = (minX + maxX) / 2, cz = (minZ + maxZ) / 2
        func slab(y: Float, thickness: CGFloat, base: UInt32, pct: Double?) -> SCNNode {
            let g = SCNBox(width: w, height: thickness, length: l, chamferRadius: 2)
            let m = SCNMaterial()
            let strength = CGFloat((pct ?? 50) / 100)
            m.diffuse.contents = UIColor(hex: base).withAlphaComponent(0.35 + 0.55 * strength)
            m.transparency = 0.9
            m.lightingModel = .lambert
            g.materials = [m]
            let n = SCNNode(geometry: g)
            n.position = SCNVector3(cx, y, cz)
            return n
        }
        scene.rootNode.addChildNode(slab(y: -40, thickness: 26, base: 0x8A5A2B, pct: soil))
        scene.rootNode.addChildNode(slab(y: -110, thickness: 40, base: 0x2F6FB5, pct: groundwater))

        let ambient = SCNNode(); ambient.light = SCNLight(); ambient.light?.type = .ambient; ambient.light?.intensity = 450
        scene.rootNode.addChildNode(ambient)
        let sun = SCNNode(); sun.light = SCNLight(); sun.light?.type = .directional; sun.light?.intensity = 900
        sun.eulerAngles = SCNVector3(-Float.pi / 3, Float.pi / 5, 0)
        scene.rootNode.addChildNode(sun)

        let camera = SCNNode()
        camera.name = "camera"
        camera.camera = SCNCamera()
        camera.camera?.zFar = 20_000
        let span = Float(max(w, l))
        camera.position = SCNVector3(cx + span * 0.15, span * 0.75, cz + span * 1.05)
        camera.look(at: SCNVector3(cx, -30, cz))
        scene.rootNode.addChildNode(camera)
        if animate {
            let start = camera.position
            camera.position = SCNVector3(start.x, start.y * 1.6, start.z * 1.3)
            SCNTransaction.begin(); SCNTransaction.animationDuration = 1.0
            camera.position = start
            SCNTransaction.commit()
        }
        return scene
    }
}
