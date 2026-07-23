import assert from "node:assert/strict";
import test from "node:test";
import {
  buildPixelGraphRaster,
  PixelGraphAvatarRenderer,
  projectWorldToStage,
} from "../pixel_graph_renderer.js";

test("pixel graph projector paints exact palette runs without filling transparency", () => {
  const graph = {
    schema_version: 1,
    frame: { width: 4, height: 3 },
    foreground_pixel_count: 3,
    palette: [
      [10, 20, 30, 255],
      [200, 150, 100, 128],
    ],
    runs: [
      { x: 1, y: 0, palette_indices: [0, 1] },
      { x: 3, y: 2, palette_indices: [0] },
    ],
  };
  const raster = buildPixelGraphRaster(graph);
  assert.equal(raster.painted, 3);
  assert.deepEqual(raster.bounds, { minX: 1, minY: 0, maxX: 3, maxY: 2 });
  assert.deepEqual([...raster.rgba.slice(4, 12)], [10, 20, 30, 255, 200, 150, 100, 128]);
  assert.deepEqual([...raster.rgba.slice(0, 4)], [0, 0, 0, 0]);
});

test("world projection matches the Rust stage projection at center depth", () => {
  const projected = projectWorldToStage({ x: 0, z: 5 }, 480, 270);
  assert.equal(projected.x, 240);
  assert.ok(projected.y > 129.6 && projected.y < 237.6);
  assert.ok(projected.scale > 1.4 && projected.scale < 2.2);
});

test("pixel graph projector rejects truncated run payloads", () => {
  assert.throws(
    () =>
      buildPixelGraphRaster({
        schema_version: 1,
        frame: { width: 2, height: 2 },
        foreground_pixel_count: 2,
        palette: [[1, 2, 3, 255]],
        runs: [{ x: 1, y: 1, palette_indices: [0, 0] }],
      }),
    /leaves its frame/,
  );
});

test("renderer falls back cleanly when workers are unavailable", () => {
  const context = {
    clearRect() {},
    drawImage() {},
    putImageData() {},
    imageSmoothingEnabled: true,
  };
  const canvas = {
    width: 1,
    height: 1,
    dataset: {},
    getContext: () => context,
  };
  const renderer = new PixelGraphAvatarRenderer(canvas, 480, 270, {
    createWorker: () => null,
    createCanvas: () => ({ width: 1, height: 1, getContext: () => context }),
    fetch: async () => {
      throw new Error("unused");
    },
  });
  assert.equal(renderer.worker, null);
  assert.equal(canvas.dataset.graphWorker, undefined);
  renderer.updateTelemetry();
  assert.equal(canvas.dataset.graphWorker, "fallback");
});

test("all semantic post-character newsroom graphs paint after the complete actor graph", () => {
  const draws = [];
  const context = {
    clearRect() {},
    drawImage(canvas) { draws.push(canvas.id); },
    putImageData() {},
    save() {},
    restore() {},
    translate() {},
    rotate() {},
    scale() {},
    imageSmoothingEnabled: true,
  };
  const canvas = {
    width: 1600,
    height: 900,
    dataset: {},
    getContext: () => context,
  };
  const renderer = new PixelGraphAvatarRenderer(canvas, 480, 270, {
    createWorker: () => null,
    createCanvas: () => ({ width: 1, height: 1, getContext: () => context }),
    fetch: async () => { throw new Error("unused"); },
  });
  renderer.cache.set("dance_ready", {
    canvas: { id: "actor" },
    width: 1254,
    height: 1254,
    bounds: { minX: 69, minY: 69, maxX: 1184, maxY: 1184 },
    painted: 1,
    entry: { source_record_id: "WJPA-221", foreground_pixel_count: 1 },
  });
  renderer.postCharacterCache.set("newsroom_main", [
    { canvas: { id: "effect" }, order: 5, id: "effect", semanticLayer: "effect" },
    { canvas: { id: "desk" }, order: 10, id: "desk", semanticLayer: "foreground" },
    {
      canvas: { id: "overlay" },
      order: 20,
      id: "overlay",
      semanticLayer: "broadcast_overlay",
    },
  ]);
  renderer.state = {
    sequence: 1,
    pose_id: "dance_ready",
    previous_pose_id: "dance_ready",
    pose_blend: 1,
    world_position: { x: 0, z: 5 },
    scene_mode: "newsroom_main",
  };

  renderer.draw();
  assert.deepEqual(draws, ["actor", "effect", "desk", "overlay"]);
});

test("canonical transparent frame placement is stable across radically different opaque bounds", () => {
  const actorDraws = [];
  const context = {
    clearRect() {},
    drawImage(...args) { actorDraws.push(args); },
    putImageData() {},
    save() {},
    restore() {},
    translate() {},
    rotate() {},
    scale() {},
    imageSmoothingEnabled: true,
  };
  const canvas = {
    width: 1600,
    height: 900,
    dataset: {},
    getContext: () => context,
  };
  const renderer = new PixelGraphAvatarRenderer(canvas, 480, 270, {
    createWorker: () => null,
    createCanvas: () => ({ width: 1, height: 1, getContext: () => context }),
    fetch: async () => { throw new Error("unused"); },
  });
  renderer.cache.set("high-padding", {
    canvas: { id: "high-padding" },
    width: 1254,
    height: 1254,
    bounds: { minX: 400, minY: 69, maxX: 900, maxY: 900 },
    entry: { source_record_id: "WJPA-A", foreground_pixel_count: 1 },
  });
  renderer.cache.set("low-padding", {
    canvas: { id: "low-padding" },
    width: 1254,
    height: 1254,
    bounds: { minX: 69, minY: 500, maxX: 1184, maxY: 1184 },
    entry: { source_record_id: "WJPA-B", foreground_pixel_count: 1 },
  });
  renderer.state = {
    sequence: 1,
    pose_id: "high-padding",
    previous_pose_id: "high-padding",
    pose_blend: 1,
    world_position: { x: 0, z: 5 },
    scene_mode: "studio",
  };
  renderer.draw();
  renderer.state = { ...renderer.state, sequence: 2, pose_id: "low-padding" };
  renderer.draw();

  assert.equal(actorDraws.length, 2);
  assert.equal(actorDraws[0][2], actorDraws[1][2]);
  assert.equal(actorDraws[0][4], actorDraws[1][4]);
});

test("authored speech and expression presentation poses replace only the visual graph", () => {
  const draws = [];
  const context = {
    clearRect() {},
    drawImage(canvas) { draws.push(canvas.id); },
    putImageData() {},
    save() {},
    restore() {},
    translate() {},
    rotate() {},
    scale() {},
    imageSmoothingEnabled: true,
  };
  const canvas = {
    width: 1600,
    height: 900,
    dataset: {},
    getContext: () => context,
  };
  const renderer = new PixelGraphAvatarRenderer(canvas, 480, 270, {
    createWorker: () => null,
    createCanvas: () => ({ width: 1, height: 1, getContext: () => context }),
    fetch: async () => { throw new Error("unused"); },
  });
  for (const id of ["idle_warm_camera_ready", "emotion_surprise"]) {
    renderer.cache.set(id, {
      canvas: { id },
      width: 1254,
      height: 1254,
      bounds: { minX: 69, minY: 69, maxX: 1184, maxY: 1184 },
      entry: { source_record_id: id, foreground_pixel_count: 1 },
    });
  }
  renderer.updateState({
    sequence: 1,
    pose_id: "idle_warm_camera_ready",
    presentation_pose_id: "emotion_surprise",
    previous_pose_id: "idle_warm_camera_ready",
    pose_blend: 1,
    expression: "surprised",
    mouth: "open_wide",
    speech_active: true,
    world_position: { x: 0, z: 5 },
    scene_mode: "studio",
  });
  renderer.draw();

  assert.deepEqual(draws, ["emotion_surprise"]);
  assert.equal(canvas.dataset.presentationPoseId, "emotion_surprise");
  assert.equal(canvas.dataset.expression, "surprised");
  assert.equal(canvas.dataset.mouth, "open_wide");
  assert.equal(canvas.dataset.speechActive, "true");
});

test("post-character catalog rejects layers that belong behind the actor", async () => {
  const context = {
    clearRect() {}, drawImage() {}, putImageData() {}, imageSmoothingEnabled: true,
  };
  const canvas = { width: 1, height: 1, dataset: {}, getContext: () => context };
  const renderer = new PixelGraphAvatarRenderer(canvas, 480, 270, {
    createWorker: () => null,
    createCanvas: () => ({ width: 1, height: 1, getContext: () => context }),
    fetch: async () => ({
      ok: true,
      json: async () => ({
        schema_version: 1,
        native_canvas: [1672, 941],
        scenes: [{
          scene_mode: "newsroom_main",
          targets: [{ id: "rear", semantic_layer: "set_piece", order: 0 }],
        }],
      }),
    }),
  });

  await assert.rejects(
    () => renderer.loadPostCharacterCatalog(),
    /contains a pre-character layer/,
  );
});
