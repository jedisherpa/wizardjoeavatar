import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";

import { AscilineStreamClient } from "../asciline_client.js";
import { CellStageRenderer } from "../canvas_renderer.js";

const root = process.argv[2];
if (!root) throw new Error("usage: verify_animation_evidence.mjs <evidence-root>");

function decodeBase64(value) {
  return new Uint8Array(Buffer.from(value, "base64"));
}

function hash64(bytes) {
  let hash = 0xcbf29ce484222325n;
  for (const byte of bytes) {
    hash ^= BigInt(byte);
    hash = BigInt.asUintN(64, hash * 0x100000001b3n);
  }
  return hash.toString(16).padStart(16, "0");
}

const crcTable = Array.from({ length: 256 }, (_, value) => {
  let crc = value;
  for (let bit = 0; bit < 8; bit += 1) crc = (crc & 1) ? 0xedb88320 ^ (crc >>> 1) : crc >>> 1;
  return crc >>> 0;
});

function crc32(bytes) {
  let crc = 0xffffffff;
  for (const byte of bytes) crc = crcTable[(crc ^ byte) & 0xff] ^ (crc >>> 8);
  return ((crc ^ 0xffffffff) >>> 0).toString(16).padStart(8, "0");
}

function rgbBytes(cells) {
  const rgb = new Uint8Array(cells.length / 4 * 3);
  for (let cell = 0; cell < cells.length / 4; cell += 1) {
    rgb[cell * 3] = cells[cell * 4 + 1];
    rgb[cell * 3 + 1] = cells[cell * 4 + 2];
    rgb[cell * 3 + 2] = cells[cell * 4 + 3];
  }
  return rgb;
}

function fakeCanvas(width, height) {
  const context = {
    imageSmoothingEnabled: true,
    createImageData(w, h) { return { width: w, height: h, data: new Uint8ClampedArray(w * h * 4) }; },
    putImageData() {},
    drawImage() {},
  };
  return { width, height, getContext() { return context; } };
}

const bundle = JSON.parse(await readFile(path.join(root, "hashes/codec-vectors.json"), "utf8"));
const rows = [];
const tagCounts = {};
let activeGroup = null;
let lastPresented = -1;
let client;
let renderer;

for (const vector of bundle.vectors) {
  if (vector.group !== activeGroup) {
    activeGroup = vector.group;
    lastPresented = -1;
    client = new AscilineStreamClient({ now: () => 0, sendControl() {} });
    client.beginGeneration({
      fps: 24,
      cols: vector.cols,
      rows: vector.rows,
      epoch: rows.length + 1,
      cellBytes: vector.cell_bytes,
      codec: 1,
    });
    const visible = fakeCanvas(vector.cols, vector.rows);
    renderer = new CellStageRenderer(visible, vector.cols, vector.rows, {
      createCanvas: (width, height) => fakeCanvas(width, height),
    });
  }
  const source = decodeBase64(vector.source_base64);
  const encoded = decodeBase64(vector.encoded_base64);
  if (!client.enqueue(encoded)) throw new Error(`vector ${vector.group}/${vector.sequence} was rejected`);
  await client.drain();
  const accepted = client.presentationQueue.takeNewestDue(Number.POSITIVE_INFINITY, lastPresented);
  if (!accepted) throw new Error(`vector ${vector.group}/${vector.sequence} was not presentation-accepted`);
  lastPresented = accepted.sequence;
  renderer.build(accepted.frame);
  const presentedRgb = new Uint8Array(source.length / 4 * 3);
  for (let cell = 0; cell < source.length / 4; cell += 1) {
    presentedRgb[cell * 3] = renderer.imageData.data[cell * 4];
    presentedRgb[cell * 3 + 1] = renderer.imageData.data[cell * 4 + 1];
    presentedRgb[cell * 3 + 2] = renderer.imageData.data[cell * 4 + 2];
  }
  const sourceRgb = rgbBytes(source);
  const decodedRgb = rgbBytes(accepted.frame);
  const record = {
    group: vector.group,
    sequence: vector.sequence,
    tag: vector.tag,
    source_cell_hash64: hash64(source),
    decoded_cell_hash64: hash64(accepted.frame),
    source_crc32: crc32(source),
    decoded_crc32: crc32(accepted.frame),
    source_rgb_hash64: hash64(sourceRgb),
    decoded_rgb_hash64: hash64(decodedRgb),
    presented_rgb_hash64: hash64(presentedRgb),
    source_equals_decoded: hash64(source) === hash64(accepted.frame),
    source_rgb_equals_decoded_rgb: hash64(sourceRgb) === hash64(decodedRgb),
    decoded_rgb_equals_presented_rgb: hash64(decodedRgb) === hash64(presentedRgb),
    presentation_queue_accepted: true,
  };
  if (!record.source_equals_decoded || !record.decoded_rgb_equals_presented_rgb) {
    throw new Error(`A/B/C parity failed for ${vector.group}/${vector.sequence}`);
  }
  rows.push(record);
  tagCounts[vector.tag] = (tagCounts[vector.tag] ?? 0) + 1;
}

for (const tag of [0, 1, 2, 3]) {
  if (!tagCounts[tag]) throw new Error(`codec tag ${tag} was not verified`);
}

await writeFile(
  path.join(root, "hashes/source-decoded-presented.ndjson"),
  `${rows.map((row) => JSON.stringify(row)).join("\n")}\n`,
);
await writeFile(
  path.join(root, "hashes/abc-parity-summary.json"),
  `${JSON.stringify({
    scope: "shipped JavaScript decoder, bounded presentation queue, and CellStageRenderer module",
    real_browser_control: false,
    vectors: rows.length,
    tag_counts: tagCounts,
    all_source_decoded_equal: rows.every((row) => row.source_equals_decoded),
    all_decoded_presented_rgb_equal: rows.every((row) => row.decoded_rgb_equals_presented_rgb),
  }, null, 2)}\n`,
);
await writeFile(
  path.join(root, "resync-scenarios.json"),
  `${JSON.stringify({
    scope: "module and Rust integration tests",
    real_browser_control: false,
    scenarios: [
      "missing delta requests one resync",
      "stale generation cannot present",
      "in-flight decode invalidated by resync",
      "reconnect bootstrap does not corrupt healthy viewer",
      "explicit resync reconstructs from a full frame",
    ],
  }, null, 2)}\n`,
);

console.log(`verified ${rows.length} A/B/C vectors across tags 0/1/2/3`);
