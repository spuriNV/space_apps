import Foundation

/// The CropLytics map style: Esri imagery under OpenFreeMap roads, borders and places (the same JSON as Android CropMap.kt),
/// plus the field, footprint and 3D-stack layers. Extrusion base and height are zoom expressions (0 at Z0, the feature's
/// b / h at Z1), so the stack rises under the fingers with no camera write.
enum MapStyle {
    static let z0 = Map3D.z0, z1 = Map3D.z1

    private static func extrusion(_ id: String, opacity: Double, minZoom: Double) -> String {
        """
        {"id":"\(id)","type":"fill-extrusion","source":"\(id)","minzoom":\(minZoom),"paint":{"fill-extrusion-color":["get","col"],
         "fill-extrusion-base":["interpolate",["linear"],["zoom"],\(z0),0,\(z1),["get","b"]],
         "fill-extrusion-height":["interpolate",["linear"],["zoom"],\(z0),0,\(z1),["get","h"]],
         "fill-extrusion-opacity":\(opacity),"fill-extrusion-vertical-gradient":true}}
        """
    }

    static let sourceIDs = ["reserves", "fp", "shadow", "field", "posts", "slab-grace", "slab-smap", "cells", "pins", "draft"]

    static var json: String {
        let sources = sourceIDs.map { "\"\($0)\":{\"type\":\"geojson\",\"data\":{\"type\":\"FeatureCollection\",\"features\":[]}}" }.joined(separator: ",")
        return """
        {"version":8,"name":"CropLytics",
         "glyphs":"https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf",
         "sources":{
          "sat":{"type":"raster","tiles":["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],"tileSize":256,"maxzoom":18,"attribution":"Imagery © Esri, Maxar, Earthstar Geographics"},
          "omt":{"type":"vector","url":"https://tiles.openfreemap.org/planet","attribution":"© OpenMapTiles © OpenStreetMap"},
          \(sources)},
         "layers":[
          {"id":"bg","type":"background","paint":{"background-color":"#0a0f15"}},
          {"id":"sat","type":"raster","source":"sat","paint":{"raster-saturation":-0.08,"raster-brightness-max":0.92}},
          {"id":"roads","type":"line","source":"omt","source-layer":"transportation","minzoom":8,"filter":["in",["get","class"],["literal",["motorway","trunk","primary"]]],"paint":{"line-color":"rgba(255,236,170,0.5)","line-width":["interpolate",["linear"],["zoom"],8,0.6,14,2.2]}},
          {"id":"admin","type":"line","source":"omt","source-layer":"boundary","filter":["all",["<=",["get","admin_level"],4],["!=",["get","maritime"],1]],"paint":{"line-color":"rgba(255,255,255,0.6)","line-width":1.1,"line-dasharray":[3,2]}},
          {"id":"place","type":"symbol","source":"omt","source-layer":"place","filter":["in",["get","class"],["literal",["city","town","state"]]],
           "layout":{"text-field":["coalesce",["get","name:en"],["get","name"]],"text-font":["Noto Sans Bold"],"text-size":["interpolate",["linear"],["zoom"],4,["match",["get","class"],"state",14,13],12,16],"text-transform":["match",["get","class"],"state","uppercase","none"],"text-padding":6},
           "paint":{"text-color":["match",["get","class"],"state","rgba(255,255,255,0.75)","#ffffff"],"text-halo-color":"rgba(5,10,16,0.85)","text-halo-width":1.5}},
          {"id":"res-casing","type":"line","source":"reserves","paint":{"line-color":"rgba(10,12,8,0.5)","line-width":3.6}},
          {"id":"res-line","type":"line","source":"reserves","paint":{"line-color":"#f1ecdd","line-opacity":0.95,"line-width":2,"line-dasharray":[3,2]}},
          {"id":"fp-fill","type":"fill","source":"fp","paint":{"fill-color":["get","color"],"fill-opacity":["interpolate",["linear"],["zoom"],8,0.1,13,0.03]}},
          {"id":"fp-line","type":"line","source":"fp","paint":{"line-color":["get","color"],"line-width":2,"line-dasharray":[2,1.5]}},
          {"id":"shadow","type":"fill","source":"shadow","minzoom":\(z0),"paint":{"fill-color":"#000000","fill-opacity":["interpolate",["linear"],["zoom"],\(z0),0,\(z1),0.42]}},
          {"id":"field-fill","type":"fill","source":"field","paint":{"fill-color":["get","tint"],"fill-opacity":["case",["get","selected"],0.45,0]}},
          {"id":"field-casing","type":"line","source":"field","paint":{"line-color":"rgba(0,0,0,0.65)","line-width":5}},
          {"id":"field-line","type":"line","source":"field","paint":{"line-color":["case",["==",["get","selected"],true],"#ffd166","rgba(255,255,255,0.75)"],"line-width":2}},
          {"id":"field-hit","type":"fill","source":"field","paint":{"fill-color":"#ffffff","fill-opacity":["interpolate",["linear"],["zoom"],9,0.2,11.5,0.01]}},
          {"id":"draft-fill","type":"fill","source":"draft","paint":{"fill-color":"#ffd166","fill-opacity":0.25}},
          {"id":"draft-line","type":"line","source":"draft","paint":{"line-color":"#ffd166","line-width":3}},
          \(extrusion("posts", opacity: 0.55, minZoom: z0 + 0.4)),
          \(extrusion("slab-grace", opacity: 0.86, minZoom: z0 + 0.1)),
          \(extrusion("slab-smap", opacity: 0.84, minZoom: z0 + 0.1)),
          \(extrusion("cells", opacity: 0.97, minZoom: 11.2)),
          {"id":"pins","type":"circle","source":"pins","paint":{"circle-radius":["case",["get","selected"],10,7],"circle-color":["case",["get","selected"],"#ffd166","#2f5d34"],"circle-stroke-color":["case",["get","selected"],"#191c16","#ffffff"],"circle-stroke-width":2}},
          {"id":"pin-names","type":"symbol","source":"pins","minzoom":8.2,"filter":["!=",["get","selected"],true],"layout":{"text-field":["get","name"],"text-font":["Noto Sans Bold"],"text-size":13,"text-anchor":"top","text-offset":[0,1],"text-optional":true},
           "paint":{"text-color":"#191c16","text-halo-color":"#f7f6f0","text-halo-width":3}},
          {"id":"pin-sel-name","type":"symbol","source":"pins","filter":["==",["get","selected"],true],"layout":{"text-field":["get","name"],"text-font":["Noto Sans Bold"],"text-size":14,"text-anchor":"bottom","text-offset":[0,-1.1],"text-allow-overlap":true},
           "paint":{"text-color":"#191c16","text-halo-color":"#f7f6f0","text-halo-width":4}}
         ]}
        """
    }

    static func writeToDisk() -> URL {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("croplytics-style.json")
        try? json.data(using: .utf8)?.write(to: url, options: .atomic)
        return url
    }
}
