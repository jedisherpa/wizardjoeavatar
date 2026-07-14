// Minimal ESM decoder for the existing Wizard ASCILINE frame protocol.
export const TAG_RAW = 0;
export const TAG_ZLIB = 1;
export const TAG_DELTA = 2;
export const TAG_RLE_FULL = 3;

export async function inflate(bytes) {
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("deflate"));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

export function parseInit(text) {
  const parts = text.split(":");
  if (parts[0] !== "INIT" || parts.length < 5) throw new Error("Invalid ASCILINE INIT message");
  const metadata = {
    fps: Number(parts[1]),
    cols: Number(parts[3]),
    rows: Number(parts[4]),
    epoch: 0,
    cellBytes: 4,
    codec: 1,
  };
  for (let index = 8; index + 1 < parts.length; index += 2) {
    if (parts[index] === "EPOCH") metadata.epoch = Number(parts[index + 1]);
    else if (parts[index] === "CELL_BYTES") metadata.cellBytes = Number(parts[index + 1]);
    else if (parts[index] === "CODEC") metadata.codec = Number(parts[index + 1]);
  }
  if (![metadata.fps, metadata.cols, metadata.rows, metadata.epoch, metadata.cellBytes, metadata.codec]
    .every(Number.isFinite)) {
    throw new Error("ASCILINE INIT metadata is not numeric");
  }
  return metadata;
}

export function inspectEnvelope(message) {
  const bytes = message instanceof Uint8Array ? message : new Uint8Array(message);
  if (bytes.byteLength < 5) throw new Error("ASCILINE frame header is truncated");
  return {
    sequence: new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength).getUint32(0, false),
    tag: bytes[4],
    bytes,
  };
}

export function makeDecoder(cellBytes = 4, inflateBytes = inflate) {
  let previous = null;

  async function decode(message) {
    const { sequence, tag, bytes } = inspectEnvelope(message);
    const payload = bytes.subarray(5);
    let frame;

    if (tag === TAG_RAW) {
      frame = payload.slice();
    } else if (tag === TAG_ZLIB) {
      frame = await inflateBytes(payload);
    } else if (tag === TAG_DELTA) {
      if (!previous) throw new Error("Delta frame without previous frame");
      const body = await inflateBytes(payload);
      if (body.length % (4 + cellBytes) !== 0) throw new Error("Malformed ASCILINE delta body");
      const count = body.length / (4 + cellBytes);
      const bodyView = new DataView(body.buffer, body.byteOffset, body.byteLength);
      const valuesOffset = count * 4;
      frame = previous.slice();
      for (let index = 0; index < count; index += 1) {
        const cellIndex = bodyView.getUint32(index * 4, true);
        const destination = cellIndex * cellBytes;
        const source = valuesOffset + index * cellBytes;
        if (destination + cellBytes > frame.length) throw new Error("ASCILINE delta index is out of range");
        frame.set(body.subarray(source, source + cellBytes), destination);
      }
    } else if (tag === TAG_RLE_FULL) {
      const body = await inflateBytes(payload);
      if (body.length % (2 + cellBytes) !== 0) throw new Error("Malformed ASCILINE RLE body");
      const bodyView = new DataView(body.buffer, body.byteOffset, body.byteLength);
      let totalCells = 0;
      for (let offset = 0; offset < body.length; offset += 2 + cellBytes) {
        totalCells += bodyView.getUint16(offset, true);
      }
      frame = new Uint8Array(totalCells * cellBytes);
      let destination = 0;
      for (let offset = 0; offset < body.length; offset += 2 + cellBytes) {
        const count = bodyView.getUint16(offset, true);
        const cell = body.subarray(offset + 2, offset + 2 + cellBytes);
        for (let run = 0; run < count; run += 1) {
          frame.set(cell, destination);
          destination += cellBytes;
        }
      }
    } else {
      throw new Error(`Unknown ASCILINE codec tag ${tag}`);
    }

    previous = frame;
    return { sequence, frame, tag, wireBytes: bytes.byteLength };
  }

  return {
    decode,
    reset() {
      previous = null;
    },
  };
}
