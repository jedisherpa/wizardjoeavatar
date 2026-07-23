const HORIZON_RATIO = 0.48;
const NEAR_ROOT_RATIO = 0.88;
const NEAR_DEPTH = 1.5;
const FAR_DEPTH = 10.0;
const CANONICAL_POSE_HEIGHT = 96;
const CANONICAL_GRAPH_SIZE = 1254;
const REPLACEMENT_POSE_COUNT = 260;

function defaultCanvasFactory(width, height) {
  if (typeof OffscreenCanvas !== "undefined") return new OffscreenCanvas(width, height);
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  return canvas;
}

function defaultWorkerFactory() {
  if (typeof Worker === "undefined") return null;
  return new Worker("/avatar/pixel_graph_worker.js", { type: "module" });
}

export function projectWorldToStage(worldPosition, cols, rows) {
  const z = Number.isFinite(worldPosition?.z) ? worldPosition.z : 5;
  const x = Number.isFinite(worldPosition?.x) ? worldPosition.x : 0;
  const depth = Math.max(0, Math.min(1, (FAR_DEPTH - z) / (FAR_DEPTH - NEAR_DEPTH)));
  const scale = 1.4 + depth * 0.8;
  const horizon = rows * HORIZON_RATIO;
  const near = rows * NEAR_ROOT_RATIO;
  return {
    x: cols * 0.5 + x * cols * 0.075 * scale,
    y: horizon + depth * (near - horizon),
    scale,
  };
}

export function buildPixelGraphRaster(graph) {
  if (graph?.schema_version !== 1) throw new Error("Unsupported pixel graph schema");
  const width = graph?.frame?.width;
  const height = graph?.frame?.height;
  if (!Number.isInteger(width) || width <= 0 || !Number.isInteger(height) || height <= 0) {
    throw new Error("Pixel graph has an invalid frame");
  }
  if (!Array.isArray(graph.palette) || graph.palette.length === 0 || !Array.isArray(graph.runs)) {
    throw new Error("Pixel graph palette/runs are missing");
  }
  const rgba = new Uint8ClampedArray(width * height * 4);
  let painted = 0;
  let minX = width;
  let minY = height;
  let maxX = -1;
  let maxY = -1;
  for (const run of graph.runs) {
    if (!Number.isInteger(run.x) || !Number.isInteger(run.y) || !Array.isArray(run.palette_indices)) {
      throw new Error("Pixel graph run is malformed");
    }
    if (run.y < 0 || run.y >= height || run.x < 0 || run.x + run.palette_indices.length > width) {
      throw new Error("Pixel graph run leaves its frame");
    }
    for (let offset = 0; offset < run.palette_indices.length; offset += 1) {
      const paletteIndex = run.palette_indices[offset];
      const color = graph.palette[paletteIndex];
      if (!color || color.length !== 4) throw new Error("Pixel graph palette index is invalid");
      const x = run.x + offset;
      const index = (run.y * width + x) * 4;
      rgba[index] = color[0];
      rgba[index + 1] = color[1];
      rgba[index + 2] = color[2];
      rgba[index + 3] = color[3];
      painted += 1;
      minX = Math.min(minX, x);
      minY = Math.min(minY, run.y);
      maxX = Math.max(maxX, x);
      maxY = Math.max(maxY, run.y);
    }
  }
  if (painted !== graph.foreground_pixel_count || painted === 0) {
    throw new Error(
      `Pixel graph painted ${painted} pixels; expected ${graph.foreground_pixel_count}`,
    );
  }
  return { width, height, rgba, bounds: { minX, minY, maxX, maxY }, painted };
}

export class PixelGraphAvatarRenderer {
  constructor(visibleCanvas, cols, rows, options = {}) {
    this.visibleCanvas = visibleCanvas;
    this.visibleContext = visibleCanvas.getContext("2d", { alpha: true });
    this.createCanvas = options.createCanvas ?? defaultCanvasFactory;
    this.createWorker = options.createWorker ?? defaultWorkerFactory;
    this.fetch = options.fetch ?? globalThis.fetch?.bind(globalThis);
    this.cols = cols;
    this.rows = rows;
    this.catalog = null;
    this.primaryEntries = new Map();
    this.sourceEntries = new Map();
    this.postCharacterScenes = new Map();
    this.postCharacterCache = new Map();
    this.postCharacterPending = new Map();
    this.cache = new Map();
    this.pending = new Map();
    this.preloadQueue = [];
    this.preloadQueued = new Set();
    this.preloadActive = false;
    this.cacheCapacity = options.cacheCapacity ?? 64;
    this.worker = null;
    this.workerRequests = new Map();
    this.nextWorkerRequestId = 1;
    this.state = null;
    this.lastDrawnSequence = -1;
    this.presentedPoseId = null;
    this.startWorker();
    this.resize(1, 1);
  }

  startWorker() {
    this.worker = this.createWorker?.() ?? null;
    if (!this.worker) return;
    this.worker.addEventListener("message", (event) => this.handleWorkerMessage(event.data));
    this.worker.addEventListener("error", (event) => {
      const error = new Error(event.message || "Pixel graph worker failed");
      for (const { reject } of this.workerRequests.values()) reject(error);
      this.workerRequests.clear();
      this.worker = null;
      this.updateTelemetry("worker_error");
    });
  }

  handleWorkerMessage(message) {
    const request = this.workerRequests.get(message?.requestId);
    if (!request) return;
    this.workerRequests.delete(message.requestId);
    if (message.type === "error") {
      request.reject(new Error(message.message || `Pose graph ${request.poseId} failed`));
    } else if (message.type === "loaded") {
      request.resolve({
        width: message.width,
        height: message.height,
        bounds: message.bounds,
        painted: message.painted,
        rgba: new Uint8ClampedArray(message.rgba),
      });
    } else {
      request.reject(new Error("Pixel graph worker returned an invalid response"));
    }
    this.updateTelemetry();
  }

  updateTelemetry(status = null) {
    this.visibleCanvas.dataset.graphCacheCount = String(this.cache.size);
    this.visibleCanvas.dataset.graphPendingCount = String(this.pending.size);
    this.visibleCanvas.dataset.graphQueueCount = String(this.preloadQueue.length);
    this.visibleCanvas.dataset.graphWorker = this.worker ? "active" : "fallback";
    if (status) this.visibleCanvas.dataset.graphStatus = status;
  }

  async loadCatalog() {
    if (!this.fetch) throw new Error("Fetch is unavailable");
    const response = await this.fetch("/api/avatar/wizard/v2/pose-graphs/catalog");
    if (!response.ok) throw new Error(`Pose graph catalog failed: ${response.status}`);
    const catalog = await response.json();
    if (
      catalog.schema_version !== 2 ||
      catalog.verified_pose_count !== REPLACEMENT_POSE_COUNT ||
      catalog.unique_semantic_pose_count !== REPLACEMENT_POSE_COUNT ||
      !Array.isArray(catalog.frame) ||
      catalog.frame[0] !== CANONICAL_GRAPH_SIZE ||
      catalog.frame[1] !== CANONICAL_GRAPH_SIZE ||
      !Array.isArray(catalog.entries) ||
      catalog.entries.length !== REPLACEMENT_POSE_COUNT
    ) {
      throw new Error("Pose graph catalog is incomplete");
    }
    this.catalog = catalog;
    this.primaryEntries.clear();
    this.sourceEntries.clear();
    for (const entry of catalog.entries) {
      this.sourceEntries.set(entry.source_record_id, entry);
      if (entry.primary_for_semantic_id) this.primaryEntries.set(entry.semantic_id, entry);
    }
    if (this.primaryEntries.size !== REPLACEMENT_POSE_COUNT) {
      throw new Error("Pose graph primary index is incomplete");
    }
    await this.loadPostCharacterCatalog();
    if (this.state) this.prefetchState(this.state);
    this.enqueuePreload(["walk_contact_left", "walk_passing_left", "walk_contact_right"]);
    this.updateTelemetry("catalog_ready");
    return catalog;
  }

  async loadPostCharacterCatalog() {
    const response = await this.fetch(
      "/api/avatar/wizard/v2/newsroom-graphs/post-character/catalog",
    );
    if (!response.ok) {
      throw new Error(`Newsroom post-character catalog failed: ${response.status}`);
    }
    const catalog = await response.json();
    if (
      catalog.schema_version !== 1 ||
      !Array.isArray(catalog.native_canvas) ||
      catalog.native_canvas.length !== 2 ||
      !Array.isArray(catalog.scenes)
    ) {
      throw new Error("Newsroom post-character catalog is invalid");
    }
    this.postCharacterScenes.clear();
    for (const scene of catalog.scenes) {
      if (!scene.scene_mode || !Array.isArray(scene.targets)) {
        throw new Error("Newsroom post-character scene is invalid");
      }
      if (
        scene.targets.some(
          (target) =>
            !["foreground", "effect", "broadcast_overlay"].includes(target.semantic_layer),
        )
      ) {
        throw new Error("Newsroom post-character catalog contains a pre-character layer");
      }
      this.postCharacterScenes.set(
        scene.scene_mode,
        [...scene.targets].sort(
          (left, right) => left.order - right.order || left.id.localeCompare(right.id),
        ),
      );
    }
    this.visibleCanvas.dataset.postCharacterStatus = "catalog_ready";
    this.visibleCanvas.dataset.postCharacterSceneCount = String(this.postCharacterScenes.size);
    if (this.state) this.ensureScenePostCharacter(this.state.scene_mode).catch(() => {});
  }

  resize(width, height) {
    this.visibleCanvas.width = width;
    this.visibleCanvas.height = height;
    this.visibleContext.imageSmoothingEnabled = false;
    this.draw();
  }

  restoreContext() {
    this.visibleContext = this.visibleCanvas.getContext("2d", { alpha: true });
    this.visibleContext.imageSmoothingEnabled = false;
    this.draw();
  }

  updateState(state) {
    if (!Number.isInteger(state?.sequence) || state.sequence < this.lastDrawnSequence) return;
    this.state = state;
    this.visibleCanvas.dataset.requestedPoseId = state.pose_id ?? "";
    this.visibleCanvas.dataset.requestedPreviousPoseId = state.previous_pose_id ?? "";
    this.visibleCanvas.dataset.stateSequence = String(state.sequence);
    this.visibleCanvas.dataset.walkPhase = String(state.walk_phase ?? 0);
    this.visibleCanvas.dataset.locomotion = state.locomotion ?? "unknown";
    this.visibleCanvas.dataset.contactMarker = state.contact_marker ?? "unknown";
    this.visibleCanvas.dataset.poseClipId = state.pose_clip_id ?? "";
    this.visibleCanvas.dataset.poseClipStep = String(state.pose_clip_step ?? "");
    this.visibleCanvas.dataset.poseClipGeneration = String(state.pose_clip_generation ?? 0);
    this.visibleCanvas.dataset.expression = state.expression ?? "neutral";
    this.visibleCanvas.dataset.mouth = state.mouth ?? "closed";
    this.visibleCanvas.dataset.speechActive = String(Boolean(state.speech_active));
    this.visibleCanvas.dataset.presentationPoseId = state.presentation_pose_id ?? state.pose_id ?? "";
    this.visibleCanvas.dataset.worldX = String(state.world_position?.x ?? 0);
    this.visibleCanvas.dataset.worldZ = String(state.world_position?.z ?? 0);
    this.visibleCanvas.dataset.sceneMode = state.scene_mode ?? "studio";
    if (typeof this.visibleCanvas.dispatchEvent === "function" && typeof CustomEvent !== "undefined") {
      this.visibleCanvas.dispatchEvent(new CustomEvent("pixelgraphstate", { detail: state }));
    }
    this.prefetchState(state);
    this.ensureScenePostCharacter(state.scene_mode).catch(() => {
      this.visibleCanvas.dataset.postCharacterStatus = "error";
    });
  }

  present() {
    if (!this.state) return false;
    this.draw();
    this.lastDrawnSequence = this.state.sequence;
    return true;
  }

  prefetchState(state) {
    if (!this.catalog) return;
    this.ensurePose(
      state.previous_pose_id,
      !this.sourceEntries.has(state.previous_pose_id),
    ).catch(() => {});
    this.ensurePose(state.pose_id, !this.sourceEntries.has(state.pose_id)).catch(() => {});
    this.ensurePose(
      state.presentation_pose_id,
      !this.sourceEntries.has(state.presentation_pose_id),
    ).catch(() => {});
  }

  async ensurePose(poseId, enqueueNeighbors = true) {
    if (!poseId || this.cache.has(poseId)) return this.cache.get(poseId) ?? null;
    if (!this.entryForPoseId(poseId)) return null;
    if (this.pending.has(poseId)) return this.pending.get(poseId);
    const load = this.loadPose(poseId).finally(() => {
      this.pending.delete(poseId);
      this.updateTelemetry();
    });
    this.pending.set(poseId, load);
    this.updateTelemetry("loading");
    const rendered = await load;
    if (enqueueNeighbors) this.enqueuePreload(rendered.entry.authored_transition_neighbors);
    return rendered;
  }

  enqueuePreload(poseIds) {
    for (const poseId of poseIds ?? []) {
      if (
        !this.entryForPoseId(poseId) ||
        this.cache.has(poseId) ||
        this.pending.has(poseId) ||
        this.preloadQueued.has(poseId)
      ) {
        continue;
      }
      this.preloadQueued.add(poseId);
      this.preloadQueue.push(poseId);
    }
    this.updateTelemetry();
    this.drainPreload();
  }

  async drainPreload() {
    if (this.preloadActive) return;
    this.preloadActive = true;
    while (this.preloadQueue.length > 0) {
      const poseId = this.preloadQueue.shift();
      this.preloadQueued.delete(poseId);
      this.updateTelemetry();
      try {
        await this.ensurePose(poseId, false);
      } catch {
        // A requested pose still retries through the priority path.
      }
      await new Promise((resolve) => setTimeout(resolve, 0));
    }
    this.preloadActive = false;
    this.updateTelemetry("ready");
  }

  async preloadPoseIds(poseIds) {
    const unique = [...new Set(poseIds ?? [])];
    if (unique.length > this.cacheCapacity) {
      throw new Error(
        `Motion needs ${unique.length} graphs but the cache can retain ${this.cacheCapacity}`,
      );
    }
    this.visibleCanvas.dataset.graphStatus = "preloading_motion";
    for (const poseId of unique) await this.ensurePose(poseId, false);
    this.visibleCanvas.dataset.graphStatus = "motion_ready";
    return unique.length;
  }

  async preloadSceneForeground(sceneMode) {
    return this.ensureScenePostCharacter(sceneMode);
  }

  async ensureScenePostCharacter(sceneMode) {
    if (!sceneMode || sceneMode === "studio") return [];
    if (this.postCharacterCache.has(sceneMode)) return this.postCharacterCache.get(sceneMode);
    const targets = this.postCharacterScenes.get(sceneMode);
    if (!targets) return [];
    if (this.postCharacterPending.has(sceneMode)) return this.postCharacterPending.get(sceneMode);
    const load = this.loadScenePostCharacter(sceneMode, targets).finally(() => {
      this.postCharacterPending.delete(sceneMode);
    });
    this.postCharacterPending.set(sceneMode, load);
    this.visibleCanvas.dataset.postCharacterStatus = "loading";
    return load;
  }

  async loadScenePostCharacter(sceneMode, targets) {
    const layers = [];
    for (const target of targets) {
      const poseId = `newsroom:${sceneMode}:${target.id}`;
      const path = `/api/avatar/wizard/v2/newsroom-graphs/post-character/${encodeURIComponent(sceneMode)}/${encodeURIComponent(target.id)}`;
      const entry = {
        source_record_id: target.id,
        foreground_pixel_count: target.foreground_pixel_count,
      };
      const raster = this.worker
        ? await this.loadPoseInWorker(poseId, path, entry)
        : await this.loadPoseInline(poseId, path, entry);
      const canvas = this.createCanvas(raster.width, raster.height);
      canvas.width = raster.width;
      canvas.height = raster.height;
      const context = canvas.getContext("2d", { alpha: true });
      context.putImageData(new ImageData(raster.rgba, raster.width, raster.height), 0, 0);
      layers.push({
        canvas,
        order: target.order,
        id: target.id,
        semanticLayer: target.semantic_layer,
      });
    }
    this.postCharacterCache.set(sceneMode, layers);
    this.visibleCanvas.dataset.postCharacterStatus = "ready";
    this.visibleCanvas.dataset.postCharacterLayerCount = String(layers.length);
    this.draw();
    return layers;
  }

  async loadPose(poseId) {
    const entry = this.entryForPoseId(poseId);
    const sourceIdentity = this.sourceEntries.has(poseId);
    const path = sourceIdentity
      ? `/api/avatar/wizard/v2/pose-graphs/source/${encodeURIComponent(poseId)}`
      : `/api/avatar/wizard/v2/pose-graphs/semantic/${encodeURIComponent(poseId)}`;
    const raster = this.worker
      ? await this.loadPoseInWorker(poseId, path, entry)
      : await this.loadPoseInline(poseId, path, entry);
    const canvas = this.createCanvas(raster.width, raster.height);
    canvas.width = raster.width;
    canvas.height = raster.height;
    const context = canvas.getContext("2d", { alpha: true });
    context.putImageData(new ImageData(raster.rgba, raster.width, raster.height), 0, 0);
    const rendered = {
      canvas,
      width: raster.width,
      height: raster.height,
      bounds: raster.bounds,
      painted: raster.painted,
      entry,
    };
    this.cache.set(poseId, rendered);
    while (this.cache.size > this.cacheCapacity) {
      const oldest = this.cache.keys().next().value;
      if (oldest === this.presentedPoseId && this.cache.size > 1) {
        const retained = this.cache.get(oldest);
        this.cache.delete(oldest);
        this.cache.set(oldest, retained);
      } else {
        this.cache.delete(oldest);
      }
    }
    this.updateTelemetry("ready");
    this.draw();
    return rendered;
  }

  entryForPoseId(poseId) {
    return this.sourceEntries.get(poseId) ?? this.primaryEntries.get(poseId) ?? null;
  }

  loadPoseInWorker(poseId, url, entry) {
    const requestId = this.nextWorkerRequestId;
    this.nextWorkerRequestId += 1;
    return new Promise((resolve, reject) => {
      this.workerRequests.set(requestId, { poseId, resolve, reject });
      this.worker.postMessage({ requestId, poseId, url, entry });
      this.updateTelemetry("loading");
    });
  }

  async loadPoseInline(poseId, url, entry) {
    const response = await this.fetch(
      url,
    );
    if (!response.ok) throw new Error(`Pose graph ${poseId} failed: ${response.status}`);
    const graph = await response.json();
    if (
      graph.source_record_id !== entry.source_record_id ||
      (entry.graph_id && graph.graph_id !== entry.graph_id) ||
      graph.foreground_pixel_count !== entry.foreground_pixel_count
    ) {
      throw new Error(`Pose graph ${poseId} does not match its catalog entry`);
    }
    return buildPixelGraphRaster(graph);
  }

  draw() {
    const context = this.visibleContext;
    const width = this.visibleCanvas.width;
    const height = this.visibleCanvas.height;
    context.clearRect(0, 0, width, height);
    if (!this.state) return;
    const handoffComplete = this.state.pose_blend >= 0.5;
    const requestedPoseId = this.state.presentation_pose_id ?? this.state.pose_id;
    const preferredPoseId = handoffComplete ? requestedPoseId : this.state.previous_pose_id;
    const poseId = this.cache.has(preferredPoseId)
      ? preferredPoseId
      : this.cache.has(this.presentedPoseId)
        ? this.presentedPoseId
        : this.cache.has(this.state.pose_id)
          ? this.state.pose_id
          : null;
    if (!poseId) {
      this.drawScenePostCharacter(context, width, height);
      return;
    }
    const pose = this.cache.get(poseId);
    this.presentedPoseId = poseId;
    this.visibleCanvas.dataset.poseId = poseId;
    this.visibleCanvas.dataset.sourceRecordId = pose.entry.source_record_id;
    this.visibleCanvas.dataset.foregroundPixelCount = String(pose.entry.foreground_pixel_count);
    this.visibleCanvas.dataset.graphStatus = "presented";
    const projected = projectWorldToStage(this.state.world_position, this.cols, this.rows);
    const logicalHeight = CANONICAL_POSE_HEIGHT * projected.scale;
    const logicalWidth = logicalHeight * (pose.width / pose.height);
    const scaleX = width / this.cols;
    const scaleY = height / this.rows;
    const transform = this.state.actor_transform ?? {};
    const offsetX = Number.isFinite(transform.offset_x) ? transform.offset_x : 0;
    const offsetY = Number.isFinite(transform.offset_y) ? transform.offset_y : 0;
    const rotation = Number.isFinite(transform.rotation_degrees)
      ? (transform.rotation_degrees * Math.PI) / 180
      : 0;
    const actorScaleX = Number.isFinite(transform.scale_x) ? transform.scale_x : 1;
    const actorScaleY = Number.isFinite(transform.scale_y) ? transform.scale_y : 1;
    context.imageSmoothingEnabled = false;
    context.save();
    context.translate((projected.x + offsetX) * scaleX, (projected.y + offsetY) * scaleY);
    context.rotate(rotation);
    context.scale(actorScaleX, actorScaleY);
    context.drawImage(
      pose.canvas,
      -logicalWidth * 0.5 * scaleX,
      -logicalHeight * scaleY,
      logicalWidth * scaleX,
      logicalHeight * scaleY,
    );
    context.restore();
    this.drawScenePostCharacter(context, width, height);
  }

  drawScenePostCharacter(context, width, height) {
    const sceneMode = this.state?.scene_mode ?? "studio";
    const layers = this.postCharacterCache.get(sceneMode) ?? [];
    for (const layer of layers) {
      context.drawImage(layer.canvas, 0, 0, width, height);
    }
  }
}
