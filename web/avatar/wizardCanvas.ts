export class WizardCanvas {
  constructor(canvas, selection) {
    this.canvas = canvas;
    this.selection = selection;
    this.ctx = canvas.getContext("2d");
    this.cols = 0;
    this.rows = 0;
    this.cellWidth = 8;
    this.cellHeight = 8;
    this.tileSize = 8;
    this.xPos = [];
    this.yPos = [];
    this.selectionBuffer = null;
    this.decoder = new TextDecoder();
  }

  configure(cols, rows) {
    this.cols = cols;
    this.rows = rows;
    this.cellWidth = 8;
    this.cellHeight = 8;
    this.tileSize = 8;
    this.ctx.imageSmoothingEnabled = false;
    this.canvas.width = cols * this.cellWidth;
    this.canvas.height = rows * this.cellHeight;
    this.canvas.style.aspectRatio = `${cols} / ${rows}`;
    this.xPos = Array.from({ length: cols }, (_, index) => index * this.cellWidth);
    this.yPos = Array.from({ length: rows }, (_, index) => index * this.cellHeight);
    this.selectionBuffer = new Uint8Array((cols + 1) * rows);
    for (let row = 0; row < rows; row++) this.selectionBuffer[row * (cols + 1) + cols] = 10;
  }

  draw(frame) {
    const ctx = this.ctx;
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    let col = 0;
    let row = 0;
    let lastColor = "";
    for (let idx = 0; idx < frame.length; idx += 4) {
      const ch = frame[idx];
      if (this.selectionBuffer) this.selectionBuffer[row * (this.cols + 1) + col] = ch;
      if (ch !== 32) {
        const color = `rgb(${frame[idx + 1]},${frame[idx + 2]},${frame[idx + 3]})`;
        if (color !== lastColor) {
          ctx.fillStyle = color;
          lastColor = color;
        }
        ctx.fillRect(this.xPos[col], this.yPos[row], this.tileSize, this.tileSize);
      }
      col++;
      if (col >= this.cols) {
        col = 0;
        row++;
      }
    }
    if (this.selection && this.selectionBuffer) {
      this.selection.textContent = this.decoder.decode(this.selectionBuffer);
    }
  }
}
