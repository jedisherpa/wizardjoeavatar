export class CompleteFrameQueue {
  constructor(capacity = 2) {
    this.capacity = capacity;
    this.items = [];
  }

  get length() {
    return this.items.length;
  }

  clear() {
    this.items.length = 0;
  }

  push(frame) {
    this.items = this.items.filter((candidate) => candidate.sequence !== frame.sequence);
    this.items.push(frame);
    this.items.sort((a, b) => a.sequence - b.sequence);
    if (this.items.length > this.capacity) this.items.splice(0, this.items.length - this.capacity);
  }

  takeNewestDue(now, lastPresentedSequence = -1) {
    const due = this.items.filter(
      (frame) => frame.presentationTime <= now && frame.sequence > lastPresentedSequence,
    );
    if (!due.length) return null;
    const selected = due[due.length - 1];
    this.items = this.items.filter((frame) => frame.sequence > selected.sequence);
    return selected;
  }
}

export function computeFixedViewport(canvasWidth, canvasHeight, cols, rows) {
  const stageAspect = cols / rows;
  const canvasAspect = canvasWidth / canvasHeight;
  const width = canvasAspect > stageAspect ? Math.floor(canvasHeight * stageAspect) : canvasWidth;
  const height = canvasAspect > stageAspect ? canvasHeight : Math.floor(canvasWidth / stageAspect);
  return {
    x: Math.floor((canvasWidth - width) / 2),
    y: Math.floor((canvasHeight - height) / 2),
    width,
    height,
  };
}

function defaultCanvasFactory(width, height) {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  return canvas;
}

export class CellStageRenderer {
  constructor(canvas, cols = 480, rows = 270, options = {}) {
    this.canvas = canvas;
    this.context = canvas.getContext("2d", { alpha: false });
    this.createCanvas = options.createCanvas || defaultCanvasFactory;
    this.queue = options.queue || new CompleteFrameQueue(2);
    this.lastFrame = null;
    this.lastPresentedSequence = -1;
    this.lastPresentedAt = -Infinity;
    this.needsRepaint = false;
    const Observer = options.ResizeObserver || globalThis.ResizeObserver;
    this.resizeObserver = Observer ? new Observer(() => this.resize()) : null;
    this.resizeObserver?.observe(canvas);
    this.configure(cols, rows);
  }

  configure(cols, rows) {
    this.cols = cols;
    this.rows = rows;
    this.logicalCanvas = this.createCanvas(cols, rows);
    this.logicalCanvas.width = cols;
    this.logicalCanvas.height = rows;
    this.logicalContext = this.logicalCanvas.getContext("2d", { alpha: false });
    this.imageData = this.logicalContext.createImageData(cols, rows);
    this.lastFrame = null;
    this.lastPresentedSequence = -1;
    this.lastPresentedAt = -Infinity;
    this.queue.clear();
    this.resize();
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    const dpr = Math.max(1, globalThis.devicePixelRatio || 1);
    const width = Math.max(1, Math.round(rect.width * dpr));
    const height = Math.max(1, Math.round(rect.height * dpr));
    if (this.canvas.width === width && this.canvas.height === height) return;
    this.canvas.width = width;
    this.canvas.height = height;
    this.needsRepaint = true;
  }

  enqueue(frame) {
    this.queue.push(frame);
  }

  clearQueue() {
    this.queue.clear();
  }

  present(now, minimumInterval = 0) {
    let candidate = null;
    if (now - this.lastPresentedAt >= minimumInterval) {
      candidate = this.queue.takeNewestDue(now, this.lastPresentedSequence);
    }
    if (candidate) {
      this.lastFrame = candidate.frame;
      this.lastPresentedSequence = candidate.sequence;
      this.lastPresentedAt = now;
      this.paint(candidate.frame);
      return candidate;
    }
    if (this.needsRepaint && this.lastFrame) this.paint(this.lastFrame);
    return null;
  }

  paint(frame) {
    if (frame.length !== this.cols * this.rows * 4) {
      throw new Error(`Decoded frame has ${frame.length} bytes; expected ${this.cols * this.rows * 4}`);
    }
    const pixels = this.imageData.data;
    for (let cell = 0; cell < this.cols * this.rows; cell += 1) {
      const offset = cell * 4;
      pixels[offset] = frame[offset + 1];
      pixels[offset + 1] = frame[offset + 2];
      pixels[offset + 2] = frame[offset + 3];
      pixels[offset + 3] = 255;
    }
    this.logicalContext.putImageData(this.imageData, 0, 0);
    const viewport = computeFixedViewport(
      this.canvas.width,
      this.canvas.height,
      this.cols,
      this.rows,
    );
    this.context.fillStyle = "#151919";
    this.context.fillRect(0, 0, this.canvas.width, this.canvas.height);
    this.context.imageSmoothingEnabled = false;
    this.context.drawImage(
      this.logicalCanvas,
      0,
      0,
      this.cols,
      this.rows,
      viewport.x,
      viewport.y,
      viewport.width,
      viewport.height,
    );
    this.needsRepaint = false;
  }

  restoreContext() {
    this.configure(this.cols, this.rows);
  }

  destroy() {
    this.resizeObserver?.disconnect();
  }
}
