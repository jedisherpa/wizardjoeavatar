export const TAG_RAW = 0;
export const TAG_ZLIB = 1;
export const TAG_DELTA = 2;
export const TAG_RLE_FULL = 3;

async function inflate(bytes) {
  const ds = new DecompressionStream("deflate");
  const stream = new Blob([bytes]).stream().pipeThrough(ds);
  const buf = await new Response(stream).arrayBuffer();
  return new Uint8Array(buf);
}

export function makeDecoder(cellBytes = 4) {
  let previous = null;

  async function decode(message) {
    const bytes = new Uint8Array(message);
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    const frameIndex = view.getUint32(0, false);
    const tag = bytes[4];
    const payload = bytes.subarray(5);
    let frame;

    if (tag === TAG_RAW) {
      frame = payload.slice();
    } else if (tag === TAG_ZLIB) {
      frame = await inflate(payload);
    } else if (tag === TAG_DELTA) {
      if (!previous) throw new Error("Delta frame without previous frame");
      const body = await inflate(payload);
      const count = body.length / (4 + cellBytes);
      const bodyView = new DataView(body.buffer, body.byteOffset, body.byteLength);
      frame = previous.slice();
      const valuesOffset = count * 4;
      for (let i = 0; i < count; i++) {
        const cellIndex = bodyView.getUint32(i * 4, true);
        const dst = cellIndex * cellBytes;
        const src = valuesOffset + i * cellBytes;
        for (let c = 0; c < cellBytes; c++) frame[dst + c] = body[src + c];
      }
    } else if (tag === TAG_RLE_FULL) {
      const body = await inflate(payload);
      const bodyView = new DataView(body.buffer, body.byteOffset, body.byteLength);
      let totalCells = 0;
      for (let offset = 0; offset < body.length; offset += 2 + cellBytes) {
        totalCells += bodyView.getUint16(offset, true);
      }
      frame = new Uint8Array(totalCells * cellBytes);
      let dst = 0;
      for (let offset = 0; offset < body.length; offset += 2 + cellBytes) {
        const count = bodyView.getUint16(offset, true);
        for (let i = 0; i < count; i++) {
          for (let c = 0; c < cellBytes; c++) frame[dst++] = body[offset + 2 + c];
        }
      }
    } else {
      throw new Error(`Unknown codec tag ${tag}`);
    }

    previous = frame;
    return { frameIndex, frame, tag };
  }

  return {
    decode,
    reset() {
      previous = null;
    },
  };
}
