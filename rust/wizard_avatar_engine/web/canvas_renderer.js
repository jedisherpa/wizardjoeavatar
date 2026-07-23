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
  if (typeof OffscreenCanvas !== "undefined") return new OffscreenCanvas(width, height);
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  return canvas;
}

export class CellStageRenderer {
  constructor(visibleCanvas, cols, rows, options = {}) {
    this.visibleCanvas = visibleCanvas;
    this.visibleContext = visibleCanvas.getContext("2d", { alpha: false });
    this.createCanvas = options.createCanvas ?? defaultCanvasFactory;
    this.queue = options.queue ?? new CompleteFrameQueue(2);
    this.lastPresentedSequence = -1;
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
    this.lastPresentedSequence = -1;
    this.hasPresentedFrame = false;
    this.queue.clear();
  }

  resize(width, height) {
    this.visibleCanvas.width = width;
    this.visibleCanvas.height = height;
    this.visibleContext.fillStyle = "#fff";
    this.visibleContext.fillRect(0, 0, width, height);
    if (this.hasPresentedFrame) this.drawLogicalFrame();
  }

  restoreContext() {
    this.configure(this.cols, this.rows);
  }

  enqueue(frame) {
    this.queue.push(frame);
  }

  present(now) {
    const candidate = this.queue.takeNewestDue(now, this.lastPresentedSequence);
    if (!candidate) return false;
    this.build(candidate.frame);
    this.hasPresentedFrame = true;
    this.drawLogicalFrame();
    this.lastPresentedSequence = candidate.sequence;
    return true;
  }

  drawLogicalFrame() {
    const viewport = computeFixedViewport(
      this.visibleCanvas.width,
      this.visibleCanvas.height,
      this.cols,
      this.rows,
    );
    this.visibleContext.imageSmoothingEnabled = false;
    this.visibleContext.fillStyle = "#fff";
    this.visibleContext.fillRect(0, 0, this.visibleCanvas.width, this.visibleCanvas.height);
    this.visibleContext.drawImage(
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
  }

  build(frame) {
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
  }
}
