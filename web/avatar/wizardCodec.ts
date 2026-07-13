export const TAG_RAW = 0;
export const TAG_ZLIB = 1;
export const TAG_DELTA = 2;
export const TAG_RLE_FULL = 3;

function messageBytes(message) {
  if (message instanceof Uint8Array) return message;
  if (message instanceof ArrayBuffer) return new Uint8Array(message);
  if (ArrayBuffer.isView(message)) {
    return new Uint8Array(message.buffer, message.byteOffset, message.byteLength);
  }
  throw new Error("Unsupported adaptive frame message type");
}

export function parseFrameHeader(message) {
  const bytes = messageBytes(message);
  if (bytes.byteLength < 5) throw new Error("Adaptive message too short");
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  return {
    bytes,
    frameIndex: view.getUint32(0, false),
    tag: bytes[4],
    payload: bytes.subarray(5),
  };
}

export function isKeyframeTag(tag) {
  return tag === TAG_RAW || tag === TAG_ZLIB || tag === TAG_RLE_FULL;
}

export function frameHash(frame) {
  const bytes = frame instanceof Uint8Array ? frame : new Uint8Array(frame);
  let value = 0x811c9dc5;
  for (let i = 0; i < bytes.length; i++) {
    value ^= bytes[i];
    value = Math.imul(value, 0x01000193) >>> 0;
  }
  return `fnv1a32:${value.toString(16).padStart(8, "0")}`;
}

async function inflate(bytes) {
  const ds = new DecompressionStream("deflate");
  const stream = new Blob([bytes]).stream().pipeThrough(ds);
  const buf = await new Response(stream).arrayBuffer();
  return new Uint8Array(buf);
}

export function makeDecoder(cellBytes = 4) {
  let previous = null;

  async function decode(message) {
    const { frameIndex, tag, payload } = parseFrameHeader(message);
    let frame;

    if (tag === TAG_RAW) {
      frame = payload.slice();
    } else if (tag === TAG_ZLIB) {
      frame = await inflate(payload);
    } else if (tag === TAG_DELTA) {
      if (!previous) throw new Error("Delta frame without previous frame");
      const body = await inflate(payload);
      const recordSize = 4 + cellBytes;
      if (body.length % recordSize !== 0) throw new Error("Malformed delta frame payload");
      const count = body.length / recordSize;
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
        if (offset + 2 + cellBytes > body.length) throw new Error("Malformed RLE frame payload");
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
