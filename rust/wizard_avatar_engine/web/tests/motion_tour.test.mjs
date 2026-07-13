import assert from "node:assert/strict";
import test from "node:test";

import {
  MOTION_TOUR_CYCLE_MS,
  MOTION_TOUR_STEPS,
  createMotionTourLoop,
} from "../motion_tour.js";

function fakeClock() {
  let nextId = 1;
  const timers = new Map();
  return {
    timers,
    schedule(callback, delay) {
      const id = nextId++;
      timers.set(id, { callback, delay });
      return id;
    },
    cancelTimer(id) {
      timers.delete(id);
    },
    runDelay(delay) {
      const match = [...timers].find(([, timer]) => timer.delay === delay);
      assert.ok(match, `expected a timer at ${delay}ms`);
      const [id, timer] = match;
      timers.delete(id);
      timer.callback();
    },
  };
}

test("motion tour repeats until it is explicitly cancelled", () => {
  const clock = fakeClock();
  const calls = [];
  const activeChanges = [];
  const loop = createMotionTourLoop({
    post(path, payload) {
      calls.push([path, payload]);
    },
    schedule: clock.schedule,
    cancelTimer: clock.cancelTimer,
    onActiveChange(active) {
      activeChanges.push(active);
    },
  });

  loop.start();
  assert.equal(loop.active, true);
  assert.equal(clock.timers.size, MOTION_TOUR_STEPS.length + 1);
  clock.runDelay(0);
  assert.equal(calls[0][0], "reset");

  clock.runDelay(MOTION_TOUR_CYCLE_MS);
  assert.equal(clock.timers.size, MOTION_TOUR_STEPS.length + 1);
  clock.runDelay(0);
  assert.deepEqual(calls.map(([path]) => path), ["reset", "reset"]);

  loop.cancel();
  assert.equal(loop.active, false);
  assert.equal(clock.timers.size, 0);
  assert.deepEqual(activeChanges, [false, true, false]);
});

test("restarting play invalidates the previous cycle before scheduling another", () => {
  const clock = fakeClock();
  const loop = createMotionTourLoop({
    post() {},
    schedule: clock.schedule,
    cancelTimer: clock.cancelTimer,
  });

  loop.start();
  const firstIds = new Set(clock.timers.keys());
  loop.start();
  assert.equal(clock.timers.size, MOTION_TOUR_STEPS.length + 1);
  assert.ok([...clock.timers.keys()].every((id) => !firstIds.has(id)));
});
