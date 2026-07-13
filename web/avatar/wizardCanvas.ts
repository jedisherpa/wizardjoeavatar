import { frameHash } from "./wizardCodec.ts";

export class WizardCanvas {
  constructor(canvas, selection) {
    this.canvas = canvas;
    this.selection = selection;
    this.ctx = canvas.getContext("2d", { alpha: false });
    this.backCanvas = document.createElement("canvas");
    this.backCtx = this.backCanvas.getContext("2d", { alpha: false });
    this.cols = 0;
    this.rows = 0;
    this.dpr = 1;
    this.deviceCell = 8;
    this.cellWidth = 8;
    this.cellHeight = 8;
    this.tileSize = 8;
    this.xPos = [];
    this.yPos = [];
    this.selectionBuffer = null;
    this.decoder = new TextDecoder();
    this.lastFrame = null;
    this.lastPresentedLogicalHash = null;
    this.lastDrawCalls = 0;
    this.framesDrawn = 0;
    this.selectionUpdates = 0;
    this.lastSelectionUpdateAt = 0;
    this.selectionUpdateIntervalMs = 500;
    this.resizeHandler = () => this.resizeToViewport();
    window.addEventListener("resize", this.resizeHandler, { passive: true });
  }

  configure(cols, rows) {
    const gridChanged = this.cols !== cols || this.rows !== rows;
    this.cols = cols;
    this.rows = rows;
    if (gridChanged) this.lastFrame = null;
    this.canvas.style.aspectRatio = `${cols} / ${rows}`;
    this.resizeToViewport();
    this.selectionBuffer = new Uint8Array((cols + 1) * rows);
    for (let row = 0; row < rows; row++) this.selectionBuffer[row * (cols + 1) + cols] = 10;
  }

  resizeToViewport() {
    if (!this.cols || !this.rows) return;
    const viewportWidth = Math.max(1, window.innerWidth || document.documentElement.clientWidth || this.cols * 8);
    const viewportHeight = Math.max(1, window.innerHeight || document.documentElement.clientHeight || this.rows * 8);
    const dpr = Math.max(1, window.devicePixelRatio || 1);
    const deviceCell = Math.max(1, Math.floor(Math.min(
      viewportWidth * dpr / this.cols,
      viewportHeight * dpr / this.rows,
    )));
    const backingWidth = this.cols * deviceCell;
    const backingHeight = this.rows * deviceCell;
    const changed = this.canvas.width !== backingWidth || this.canvas.height !== backingHeight;

    this.dpr = dpr;
    this.deviceCell = deviceCell;
    this.cellWidth = deviceCell;
    this.cellHeight = deviceCell;
    this.tileSize = deviceCell;
    this.canvas.width = backingWidth;
    this.canvas.height = backingHeight;
    this.backCanvas.width = backingWidth;
    this.backCanvas.height = backingHeight;
    this.canvas.style.width = `${backingWidth / dpr}px`;
    this.canvas.style.height = `${backingHeight / dpr}px`;
    this.ctx.imageSmoothingEnabled = false;
    this.backCtx.imageSmoothingEnabled = false;
    this.xPos = Array.from({ length: this.cols }, (_, index) => index * deviceCell);
    this.yPos = Array.from({ length: this.rows }, (_, index) => index * deviceCell);

    if (changed && this.lastFrame) this.draw(this.lastFrame);
  }

  draw(frame) {
    if (!this.cols || !this.rows) return;
    this.lastFrame = frame;
    this.lastPresentedLogicalHash = frameHash(frame);
    const ctx = this.backCtx;
    const now = performance.now();
    const shouldSyncSelection = this.selection && this.selectionBuffer
      && now - this.lastSelectionUpdateAt >= this.selectionUpdateIntervalMs;
    let drawCalls = 1;

    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, this.backCanvas.width, this.backCanvas.height);

    let lastColor = "";
    for (let row = 0; row < this.rows; row++) {
      let runStart = -1;
      let runColor = "";
      const rowOffset = row * this.cols * 4;
      const y = this.yPos[row];

      const flushRun = (endCol) => {
        if (runStart < 0) return;
        const color = `rgb(${runColor})`;
        if (color !== lastColor) {
          ctx.fillStyle = color;
          lastColor = color;
        }
        ctx.fillRect(
          this.xPos[runStart],
          y,
          (endCol - runStart) * this.tileSize,
          this.tileSize,
        );
        drawCalls++;
      };

      for (let col = 0; col < this.cols; col++) {
        const idx = rowOffset + col * 4;
        const ch = frame[idx];
        if (shouldSyncSelection) this.selectionBuffer[row * (this.cols + 1) + col] = ch;
        const color = ch === 32 ? "" : `${frame[idx + 1]},${frame[idx + 2]},${frame[idx + 3]}`;
        if (color === runColor) continue;
        flushRun(col);
        runStart = color ? col : -1;
        runColor = color;
      }
      flushRun(this.cols);
    }

    this.ctx.imageSmoothingEnabled = false;
    this.ctx.drawImage(this.backCanvas, 0, 0);
    this.lastDrawCalls = drawCalls;
    this.framesDrawn++;

    if (shouldSyncSelection) {
      this.selection.textContent = this.decoder.decode(this.selectionBuffer);
      this.selectionUpdates++;
      this.lastSelectionUpdateAt = now;
    }
  }

  getMetrics() {
    return {
      cols: this.cols,
      rows: this.rows,
      dpr: this.dpr,
      deviceCell: this.deviceCell,
      backingWidth: this.canvas.width,
      backingHeight: this.canvas.height,
      cssWidth: this.canvas.style.width,
      cssHeight: this.canvas.style.height,
      lastDrawCalls: this.lastDrawCalls,
      framesDrawn: this.framesDrawn,
      selectionUpdates: this.selectionUpdates,
      lastPresentedLogicalHash: this.lastPresentedLogicalHash,
    };
  }
}
