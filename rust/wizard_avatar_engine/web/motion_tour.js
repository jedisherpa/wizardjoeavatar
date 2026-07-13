export const MOTION_TOUR_CYCLE_MS = 27000;

export const MOTION_TOUR_STEPS = Object.freeze([
  [0, "reset"],
  [250, "expression", { expression: "happy" }],
  [550, "speak", { text: "A wizard can walk, talk, and gesture at the same time.", duration_ms: 4200 }],
  [650, "path", { points: [{ x: -2.2, z: 4.6 }, { x: 2.2, z: 4.6 }, { x: 1.7, z: 6.2 }, { x: -1.7, z: 5.8 }], loop: false, speed: 1.45 }],
  [1800, "action", { action: "explaining", duration_ms: 1700 }],
  [3300, "action", { action: "pointing", duration_ms: 1500 }],
  [5000, "circle", { center_x: 0, center_z: 5.4, radius: 1.35, duration_seconds: 5.2, clockwise: true }],
  [7200, "action", { action: "magic_cast", duration_ms: 2300 }],
  [10300, "circle", { center_x: 0, center_z: 5.4, radius: 1.35, duration_seconds: 5.2, clockwise: false }],
  [14100, "figure-eight", { center_x: 0, center_z: 5.5, radius: 1.25, speed: 1.55 }],
  [17400, "speak", { text: "Speech mouth shapes stay independent from walking.", duration_ms: 3400 }],
  [22600, "return-to-center"],
  [25200, "stop"],
]);

export function createMotionTourLoop({
  post,
  schedule = setTimeout,
  cancelTimer = clearTimeout,
  onActiveChange = () => {},
}) {
  let generation = 0;
  let active = false;
  let timers = [];

  function cancel() {
    generation += 1;
    active = false;
    for (const timer of timers) cancelTimer(timer);
    timers = [];
    onActiveChange(false);
  }

  function scheduleCycle(token) {
    for (const [delay, path, payload = {}] of MOTION_TOUR_STEPS) {
      timers.push(schedule(() => {
        if (active && token === generation) post(path, payload);
      }, delay));
    }
    timers.push(schedule(() => {
      if (!active || token !== generation) return;
      for (const timer of timers) cancelTimer(timer);
      timers = [];
      scheduleCycle(token);
    }, MOTION_TOUR_CYCLE_MS));
  }

  function start() {
    cancel();
    active = true;
    onActiveChange(true);
    scheduleCycle(generation);
  }

  return {
    start,
    cancel,
    get active() {
      return active;
    },
  };
}
