// Terra Draw wired to the map. Loaded on demand (dynamic import from DrawLayer), so the drawing library is not in the
// first download. One polygon at a time: a rectangle (drag, or tap two corners) or a shape (tap each corner; tap the first
// point, or the last one again, to finish), then handles to reshape it.
import type maplibregl from 'maplibre-gl';
import { TerraDraw, TerraDrawPolygonMode, TerraDrawRectangleMode, TerraDrawSelectMode } from 'terra-draw';
import { TerraDrawMapLibreGLAdapter } from 'terra-draw-maplibre-gl-adapter';
import type { Polygon } from '../../myFields';

export type DrawKind = 'rect' | 'shape';
export interface DrawEvents {
  /** the ring changed (drawing or reshaping): for the live acres */
  onRing: (ring: number[][] | null) => void;
  /** a shape was finished: handles are showing */
  onFinished: () => void;
}
const INK = '#191c16', YELLOW = '#ffd166', WHITE = '#ffffff';

export function createDraw(map: maplibregl.Map, ev: DrawEvents) {
  const look = { fillColor: YELLOW, fillOpacity: 0.22, outlineColor: YELLOW, outlineWidth: 3,
    closingPointColor: WHITE, closingPointWidth: 9, closingPointOutlineColor: INK, closingPointOutlineWidth: 2,
    coordinatePointColor: WHITE, coordinatePointWidth: 6, coordinatePointOutlineColor: INK, coordinatePointOutlineWidth: 2 } as const;
  const handles = { feature: { draggable: true, coordinates: { midpoints: true, draggable: true, deletable: true } } };
  const draw = new TerraDraw({
    adapter: new TerraDrawMapLibreGLAdapter({ map, minPixelDragDistanceDrawing: 4, minPixelDragDistanceSelecting: 6 }),
    modes: [
      new TerraDrawPolygonMode({ styles: look, showCoordinatePoints: false }),
      new TerraDrawRectangleMode({ styles: look, drawInteraction: 'click-move-or-drag' }),
      new TerraDrawSelectMode({
        flags: { polygon: handles, rectangle: { feature: { draggable: true, coordinates: { draggable: true, resizable: 'opposite' } } } },
        styles: { selectedPolygonColor: YELLOW, selectedPolygonFillOpacity: 0.22, selectedPolygonOutlineColor: YELLOW, selectedPolygonOutlineWidth: 3,
          selectionPointColor: WHITE, selectionPointWidth: 10, selectionPointOutlineColor: INK, selectionPointOutlineWidth: 2,
          midPointColor: YELLOW, midPointWidth: 6, midPointOutlineColor: INK, midPointOutlineWidth: 1.5 },
      }),
    ],
  });
  let current: string | null = null; // the one feature (a finished or loaded shape)
  let keep = false; // keep the handles showing: a tap elsewhere must not deselect the shape
  const ringOf = () => {
    const f = draw.getSnapshot().find((x) => x.geometry.type === 'Polygon');
    return f ? (f.geometry as Polygon).coordinates[0] ?? null : null;
  };
  draw.on('change', () => ev.onRing(ringOf()));
  draw.on('finish', (id, ctx) => {
    if (ctx.action !== 'draw') return;
    current = String(id);
    // finishing runs inside the pointer handler: switch to the handles once it has returned
    setTimeout(() => { keep = true; draw.setMode('select'); draw.selectFeature(id); ev.onFinished(); }, 0);
  });
  draw.on('deselect', (id) => { if (keep && String(id) === current) setTimeout(() => { try { draw.selectFeature(id); } catch { /* the shape is gone */ } }, 0); });
  draw.start();
  return {
    mode(kind: DrawKind) { keep = false; current = null; draw.clear(); ev.onRing(null); draw.setMode(kind === 'rect' ? 'rectangle' : 'polygon'); },
    /** show an existing outline with handles (Redraw, or fixing a rejected outline) */
    load(g: Polygon) {
      keep = false; draw.clear();
      draw.addFeatures([{ type: 'Feature', geometry: { type: 'Polygon', coordinates: [g.coordinates[0]] }, properties: { mode: 'polygon' } }]);
      const id = draw.getSnapshot().find((x) => x.geometry.type === 'Polygon')?.id;
      if (id == null) return;
      current = String(id); keep = true;
      draw.setMode('select'); draw.selectFeature(id);
      ev.onRing(ringOf()); ev.onFinished();
    },
    /** the drawn outline as GeoJSON, or null */
    polygon(): Polygon | null {
      const ring = ringOf();
      if (!ring || ring.length < 4) return null;
      return { type: 'Polygon', coordinates: [ring.map((p) => [Math.round(p[0] * 1e6) / 1e6, Math.round(p[1] * 1e6) / 1e6])] };
    },
    clear() { keep = false; current = null; draw.clear(); ev.onRing(null); },
    destroy() { keep = false; try { draw.clear(); draw.stop(); } catch { /* already stopped */ } },
  };
}
export type DrawHandle = ReturnType<typeof createDraw>;
