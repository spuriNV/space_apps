// Terra Draw wired to the map. Loaded on demand (dynamic import from DrawLayer), so the drawing library is not in the
// first download. Four tools: Rectangle (drag, or tap two corners), Circle (drag out from the centre), Shape (tap each
// corner; tap the first point to finish) and Freehand (draw with a finger or the mouse). Every finished shape stays on the
// map with handles; "Add another shape" makes another part of the same field, "Cut a hole" makes an inner ring of the part it
// sits in. The result is a Polygon (one part, holes allowed) or a MultiPolygon.
import type maplibregl from 'maplibre-gl';
import { TerraDraw, TerraDrawCircleMode, TerraDrawFreehandMode, TerraDrawPolygonMode, TerraDrawRectangleMode, TerraDrawSelectMode, type HexColor } from 'terra-draw';
import { TerraDrawMapLibreGLAdapter } from 'terra-draw-maplibre-gl-adapter';
import { openRing, partsOf, type Geom } from '../../myFields';

export type DrawKind = 'rect' | 'circle' | 'shape' | 'free';
export type DrawRole = 'part' | 'hole';
export interface Shape { ring: number[][]; hole: boolean }
export interface DrawEvents {
  /** every shape on the map changed (drawing or reshaping): for the live total acres */
  onShapes: (shapes: Shape[]) => void;
  /** a shape was finished: handles are showing */
  onFinished: () => void;
}
const INK = '#191c16', YELLOW = '#ffd166', WHITE = '#ffffff', RED = '#ff8a7a';
const MAX_VERTICES = 380; // the API takes 400 in all
const MODES: Record<DrawKind, string> = { rect: 'rectangle', circle: 'circle', shape: 'polygon', free: 'freehand' };

type F = { id?: string | number; properties: Record<string, unknown> };
const pointIn = (p: number[], ring: number[][]) => {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    if (yi > p[1] !== yj > p[1] && p[0] < ((xj - xi) * (p[1] - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
};
/** Douglas-Peucker on a closed ring; tolerance in degrees. */
function simplify(ring: number[][], tol: number): number[][] {
  const pts = openRing(ring);
  if (pts.length <= 4) return ring;
  const keep = new Array(pts.length).fill(false);
  keep[0] = keep[pts.length - 1] = true;
  const dist = (p: number[], a: number[], b: number[]) => {
    const dx = b[0] - a[0], dy = b[1] - a[1], l = dx * dx + dy * dy;
    const t = l ? Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l)) : 0;
    return Math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy);
  };
  const rec = (i: number, j: number) => {
    let max = 0, at = -1;
    for (let k = i + 1; k < j; k++) { const d = dist(pts[k], pts[i], pts[j]); if (d > max) { max = d; at = k; } }
    if (at >= 0 && max > tol) { keep[at] = true; rec(i, at); rec(at, j); }
  };
  rec(0, pts.length - 1);
  const out = pts.filter((_, i) => keep[i]);
  return out.length >= 3 ? [...out, out[0]] : ring;
}

export function createDraw(map: maplibregl.Map, ev: DrawEvents) {
  const holes = new Set<string>();
  let pendingRole: DrawRole = 'part';
  const isHole = (f: F) => holes.has(String(f.id)) || (pendingRole === 'hole' && !!f.properties.currentlyDrawing);
  const c = (part: HexColor, hole: HexColor) => (f: F) => (isHole(f) ? hole : part);
  const look = { fillColor: c(YELLOW, RED), fillOpacity: 0.22, outlineColor: c(YELLOW, RED), outlineWidth: 3,
    closingPointColor: WHITE, closingPointWidth: 9, closingPointOutlineColor: INK, closingPointOutlineWidth: 2,
    coordinatePointColor: WHITE, coordinatePointWidth: 6, coordinatePointOutlineColor: INK, coordinatePointOutlineWidth: 2 } as never;
  const handles = { feature: { draggable: true, coordinates: { midpoints: true, draggable: true, deletable: true } } };
  const draw = new TerraDraw({
    adapter: new TerraDrawMapLibreGLAdapter({ map, minPixelDragDistanceDrawing: 4, minPixelDragDistanceSelecting: 6 }),
    modes: [
      new TerraDrawPolygonMode({ styles: look, showCoordinatePoints: false }),
      new TerraDrawRectangleMode({ styles: look, drawInteraction: 'click-move-or-drag' }),
      new TerraDrawCircleMode({ styles: look, drawInteraction: 'click-move-or-drag', segments: 32 }),
      new TerraDrawFreehandMode({ styles: look }),
      new TerraDrawSelectMode({
        flags: { polygon: handles, freehand: handles, rectangle: { feature: { draggable: true, coordinates: { draggable: true, resizable: 'opposite' } } },
          circle: { feature: { draggable: true, coordinates: { draggable: true, resizable: 'center-fixed' } } } },
        styles: { selectedPolygonColor: c(YELLOW, RED), selectedPolygonFillOpacity: 0.22, selectedPolygonOutlineColor: c(YELLOW, RED), selectedPolygonOutlineWidth: 3,
          selectionPointColor: WHITE, selectionPointWidth: 10, selectionPointOutlineColor: INK, selectionPointOutlineWidth: 2,
          midPointColor: YELLOW, midPointWidth: 6, midPointOutlineColor: INK, midPointOutlineWidth: 1.5 } as never,
      }),
    ],
  });
  let current: string | null = null; // the shape showing handles
  let keep = false; // keep the handles showing: a tap on empty map must not deselect the shape
  const polys = () => draw.getSnapshot().filter((x) => x.geometry.type === 'Polygon');
  const shapes = (): Shape[] => polys().map((f) => ({ ring: (f.geometry as { coordinates: number[][][] }).coordinates[0], hole: holes.has(String(f.id)) }));
  draw.on('change', () => ev.onShapes(shapes()));
  draw.on('finish', (id, ctx) => {
    if (ctx.action !== 'draw') return;
    current = String(id);
    if (pendingRole === 'hole') holes.add(current);
    // finishing runs inside the pointer handler: switch to the handles once it has returned
    setTimeout(() => { keep = true; draw.setMode('select'); draw.selectFeature(id); ev.onShapes(shapes()); ev.onFinished(); }, 0);
  });
  draw.on('select', (id) => { current = String(id); });
  draw.on('deselect', (id) => { if (keep && String(id) === current) setTimeout(() => { try { draw.selectFeature(id); } catch { /* the shape is gone */ } }, 0); });
  draw.start();
  const select = (id: string | number) => { current = String(id); keep = true; draw.setMode('select'); draw.selectFeature(id); };
  return {
    /** start drawing a shape; the earlier ones stay on the map */
    mode(kind: DrawKind, role: DrawRole = 'part') { keep = false; pendingRole = role; draw.setMode(MODES[kind]); },
    /** show an existing outline (all parts and holes) with handles: Redraw, or fixing a rejected outline */
    load(g: Geom) {
      keep = false; draw.clear(); holes.clear();
      const rings: { ring: number[][]; hole: boolean }[] = partsOf(g).flatMap((p) => p.map((ring, i) => ({ ring, hole: i > 0 })));
      draw.addFeatures(rings.map((r) => ({ type: 'Feature' as const, geometry: { type: 'Polygon' as const, coordinates: [r.ring] }, properties: { mode: 'polygon' } })));
      const ids = polys().map((f) => f.id as string | number);
      ids.forEach((id, i) => { if (rings[i]?.hole) holes.add(String(id)); });
      if (ids.length) select(ids[0]);
      ev.onShapes(shapes()); ev.onFinished();
    },
    /** the drawn outline as GeoJSON, or why it cannot be used yet */
    geometry(): { geom: Geom | null; error?: string } {
      const round = (r: number[][]) => r.map((p) => [Math.round(p[0] * 1e6) / 1e6, Math.round(p[1] * 1e6) / 1e6]);
      let all = shapes().filter((s) => s.ring.length >= 4);
      if (!all.length) return { geom: null };
      for (let tol = 0; all.reduce((a, s) => a + openRing(s.ring).length, 0) > MAX_VERTICES && tol < 1e-3; tol = tol ? tol * 2 : 5e-6) all = all.map((s) => ({ ...s, ring: simplify(s.ring, tol) }));
      const parts = all.filter((s) => !s.hole).map((s) => [round(s.ring)]);
      if (!parts.length) return { geom: null, error: 'Draw a shape for the field first. A hole needs a shape around it.' };
      for (const h of all.filter((s) => s.hole)) {
        const o = openRing(h.ring), at = [o.reduce((a, p) => a + p[0], 0) / o.length, o.reduce((a, p) => a + p[1], 0) / o.length];
        const home = all.filter((s) => !s.hole).findIndex((s) => pointIn(at, s.ring) && pointIn(o[0], s.ring));
        if (home < 0) return { geom: null, error: 'A hole sits outside every shape. Move it inside a shape, or remove it.' };
        parts[home].push(round(h.ring));
      }
      return { geom: parts.length === 1 ? { type: 'Polygon', coordinates: parts[0] } : { type: 'MultiPolygon', coordinates: parts } };
    },
    /** drop the shape showing handles; the next one takes over */
    removeSelected() {
      if (current == null) return;
      holes.delete(current); draw.removeFeatures([current]); current = null;
      const next = polys()[0]?.id;
      if (next != null) select(next);
      ev.onShapes(shapes());
    },
    count: () => polys().length,
    /** stop drawing and show handles on the shapes already there */
    edit() { keep = false; const id = polys()[0]?.id; if (id != null) { select(id); ev.onFinished(); } },
    clear() { keep = false; current = null; holes.clear(); draw.clear(); ev.onShapes([]); },
    destroy() { keep = false; try { draw.clear(); draw.stop(); } catch { /* already stopped */ } },
  };
}
export type DrawHandle = ReturnType<typeof createDraw>;
