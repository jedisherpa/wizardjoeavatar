import { frameHash } from "./wizardCodec.ts";

const DENSE_PIXEL_THRESHOLD = 262144;

export class WizardCanvas {
  constructor(canvas, selection) {
    this.canvas = canvas;
    this.selection = selection;
    this.ctx = canvas.getContext("2d", { alpha: true });
    this.backCanvas = document.createElement("canvas");
    this.backCtx = this.backCanvas.getContext("2d", { alpha: true });
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
    this.renderMode = "cells";
    this.denseImageData = null;
    this.lastPresentedLogicalHash = null;
    this.lastDrawCalls = 0;
    this.framesDrawn = 0;
    this.selectionUpdates = 0;
    this.lastSelectionUpdateAt = 0;
    this.selectionUpdateIntervalMs = 500;
    this.resizeHandler = () => this.resizeToViewport();
    window.addEventListener("resize", this.resizeHandler, { passive: true });
  }

  configure(cols, rows, renderMode = "cells") {
    const resolvedMode = renderMode === "rgba" || cols * rows >= DENSE_PIXEL_THRESHOLD
      ? renderMode === "rgba" ? "rgba" : "dense-cells"
      : "cells";
    const gridChanged = this.cols !== cols || this.rows !== rows || this.renderMode !== resolvedMode;
    this.cols = cols;
    this.rows = rows;
    this.renderMode = resolvedMode;
    if (gridChanged) this.lastFrame = null;
    if (gridChanged) this.denseImageData = null;
    this.canvas.style.aspectRatio = `${cols} / ${rows}`;
    this.resizeToViewport();
    this.selectionBuffer = this.renderMode === "cells" ? new Uint8Array((cols + 1) * rows) : null;
    if (this.selectionBuffer) {
      for (let row = 0; row < rows; row++) this.selectionBuffer[row * (cols + 1) + cols] = 10;
    }
  }

  resizeToViewport() {
    if (!this.cols || !this.rows) return;
    const viewportWidth = Math.max(1, window.innerWidth || document.documentElement.clientWidth || this.cols * 8);
    const viewportHeight = Math.max(1, window.innerHeight || document.documentElement.clientHeight || this.rows * 8);
    const dpr = Math.max(1, window.devicePixelRatio || 1);
    if (this.renderMode !== "cells") {
      const aspect = this.cols / this.rows;
      const cssWidth = Math.max(1, Math.min(viewportWidth, viewportHeight * aspect, this.cols));
      const cssHeight = cssWidth / aspect;
      const changed = this.canvas.width !== this.cols || this.canvas.height !== this.rows;
      this.dpr = dpr;
      this.deviceCell = 1;
      this.cellWidth = 1;
      this.cellHeight = 1;
      this.tileSize = 1;
      if (changed) {
        this.canvas.width = this.cols;
        this.canvas.height = this.rows;
        this.backCanvas.width = this.cols;
        this.backCanvas.height = this.rows;
      }
      this.canvas.style.width = `${cssWidth}px`;
      this.canvas.style.height = `${cssHeight}px`;
      this.ctx.imageSmoothingEnabled = false;
      this.backCtx.imageSmoothingEnabled = false;
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      this.xPos = [];
      this.yPos = [];
      if (this.lastFrame) this.draw(this.lastFrame);
      return;
    }
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
    if (changed) {
      this.canvas.width = backingWidth;
      this.canvas.height = backingHeight;
      this.backCanvas.width = backingWidth;
      this.backCanvas.height = backingHeight;
    }
    const nativeCssWidth = backingWidth / dpr;
    const nativeCssHeight = backingHeight / dpr;
    const presentationScale = Math.min(
      1,
      viewportWidth / nativeCssWidth,
      viewportHeight / nativeCssHeight,
    );
    this.canvas.style.width = `${nativeCssWidth * presentationScale}px`;
    this.canvas.style.height = `${nativeCssHeight * presentationScale}px`;
    this.ctx.imageSmoothingEnabled = false;
    this.backCtx.imageSmoothingEnabled = false;
    this.xPos = Array.from({ length: this.cols }, (_, index) => index * deviceCell);
    this.yPos = Array.from({ length: this.rows }, (_, index) => index * deviceCell);

    if (changed && this.lastFrame) this.draw(this.lastFrame);
  }

  draw(frame) {
    if (!this.cols || !this.rows) return;
    if (this.renderMode !== "cells") {
      this.drawDense(frame, this.renderMode === "rgba");
      return;
    }
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

  drawDense(frame, rgba = false) {
    const expectedBytes = this.cols * this.rows * 4;
    if (frame.length !== expectedBytes) throw new Error("Dense projector frame size mismatch");
    this.lastFrame = frame;
    this.lastPresentedLogicalHash = rgba ? null : frameHash(frame);
    if (!this.denseImageData || this.denseImageData.data.length !== expectedBytes) {
      this.denseImageData = this.backCtx.createImageData(this.cols, this.rows);
    }
    const target = this.denseImageData.data;
    if (rgba) {
      target.set(frame);
    } else {
      for (let offset = 0; offset < expectedBytes; offset += 4) {
        if (frame[offset] === 32) {
          target[offset] = 255;
          target[offset + 1] = 255;
          target[offset + 2] = 255;
        } else {
          target[offset] = frame[offset + 1];
          target[offset + 1] = frame[offset + 2];
          target[offset + 2] = frame[offset + 3];
        }
        target[offset + 3] = 255;
      }
    }
    let firstOpaquePixel = -1;
    for (let offset = 3; offset < target.length; offset += 4) {
      if (target[offset] > 0) {
        firstOpaquePixel = (offset - 3) / 4;
        break;
      }
    }
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    this.ctx.putImageData(this.denseImageData, 0, 0);
    if (firstOpaquePixel >= 0) {
      const sampleX = firstOpaquePixel % this.cols;
      const sampleY = Math.floor(firstOpaquePixel / this.cols);
      const projected = this.ctx.getImageData(sampleX, sampleY, 1, 1).data;
      this.canvas.dataset.projectedSample = Array.from(projected).join(",");
    }
    this.lastDrawCalls = 1;
    this.framesDrawn++;
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
      renderMode: this.renderMode,
    };
  }
}
