import assert from "node:assert/strict";
import test from "node:test";

import {
  buildNewsroomCue,
  NEWSROOM_COMMANDS,
  newsroomCommandLabel,
} from "../newsroom_controls.js";

test("newsroom UI exposes the complete Rust semantic command set", () => {
  assert.equal(NEWSROOM_COMMANDS.length, 19);
  assert.deepEqual(new Set(NEWSROOM_COMMANDS).size, 19);
  assert.equal(newsroomCommandLabel("reveal_graphic"), "reveal graphic");
});

test("ordinary newsroom cues satisfy the versioned Rust wire contract", () => {
  const cue = buildNewsroomCue({
    command: "explain",
    sequence: 12,
    intensity: 0.72,
    sensitivity: "serious",
    reducedMotion: true,
  });
  assert.equal(cue.schema_version, "newsroom_wizard_v1");
  assert.equal(cue.cue_id, "ui-1-12-explain");
  assert.equal(cue.count, null);
  assert.equal(cue.intensity, 0.72);
  assert.equal(cue.sensitivity, "serious");
  assert.equal(cue.reduced_motion, true);
  assert.equal(cue.graphic_id, null);
  assert.equal(cue.source_id, null);
});

test("specialized cues receive their required payload fields", () => {
  const count = buildNewsroomCue({ command: "count", sequence: 1, count: 3 });
  const graphic = buildNewsroomCue({ command: "reveal_graphic", sequence: 2 });
  const source = buildNewsroomCue({ command: "reveal_source", sequence: 3 });
  assert.equal(count.count, 3);
  assert.equal(graphic.graphic_id, "ui-graphic-2");
  assert.equal(source.source_id, "ui-source-3");
});

test("cue construction bounds user-controlled values", () => {
  assert.equal(buildNewsroomCue({ command: "anchor", sequence: 1, intensity: 5 }).intensity, 1);
  assert.equal(buildNewsroomCue({ command: "count", sequence: 2, count: 9 }).count, 3);
  assert.throws(() => buildNewsroomCue({ command: "dance", sequence: 1 }), /unknown newsroom command/);
  assert.throws(() => buildNewsroomCue({ command: "anchor", sequence: 0 }), /sequence must be positive/);
});
