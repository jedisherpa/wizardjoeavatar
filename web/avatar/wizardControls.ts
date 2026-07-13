import { command } from "./wizardClient.ts";

const expressionKeys = {
  "1": "neutral",
  "2": "happy",
  "3": "thinking",
  "4": "surprised",
  "5": "skeptical",
};

export function installControls() {
  document.querySelectorAll("[data-demo]").forEach((button) => {
    button.addEventListener("click", () => {
      playDemo(button).catch(console.error);
    });
  });

  document.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", () => {
      command("action", { action: button.dataset.action, duration_ms: 1800 }).catch(console.error);
    });
  });

  window.addEventListener("keydown", (event) => {
    if (event.repeat) return;
    const key = event.key.toLowerCase();
    if (expressionKeys[event.key]) {
      command("expression", { expression: expressionKeys[event.key] }).catch(console.error);
      return;
    }
    if (key === "w" || event.key === "ArrowUp") command("move", { x: 0, z: 7.0 }).catch(console.error);
    else if (key === "s" || event.key === "ArrowDown") command("move", { x: 0, z: 3.0 }).catch(console.error);
    else if (key === "a" || event.key === "ArrowLeft") command("move", { x: -2.5, z: 5.0 }).catch(console.error);
    else if (key === "d" || event.key === "ArrowRight") command("move", { x: 2.5, z: 5.0 }).catch(console.error);
    else if (key === "q") command("face", { direction: "left" }).catch(console.error);
    else if (key === "e") command("face", { direction: "right" }).catch(console.error);
    else if (key === "i") command("action", { action: "idle", duration_ms: 0 }).catch(console.error);
    else if (key === "p") command("action", { action: "pointing", duration_ms: 1800 }).catch(console.error);
    else if (key === "x") command("action", { action: "explaining", duration_ms: 2200 }).catch(console.error);
    else if (key === "c") command("action", { action: "magic_cast", duration_ms: 1800 }).catch(console.error);
    else if (key === "r") command("action", { action: "reaction", duration_ms: 1400 }).catch(console.error);
    else if (key === " ") command("stop", {}).catch(console.error);
    else if (event.key === "Home") command("move", { x: 0, z: 5.0 }).catch(console.error);
    else if (key === "o") command("circle", { center_x: 0, center_z: 5, radius: 2, clockwise: !event.shiftKey, duration_seconds: 10 }).catch(console.error);
  });
}

async function playDemo(button) {
  if (button.dataset.playing === "true") return;
  button.dataset.playing = "true";
  button.disabled = true;
  try {
    await command("reset", {});
    const clips = [
      ["ground_walk", 1300],
      ["ground_run", 1700],
      ["hover_flap", 1450],
      ["bank_glide", 2200],
      ["staff_combo", 1900],
      ["reaction_recover", 1800],
      ["celebrate", 1500],
      ["conversation", 1700],
    ];

    await command("path", {
      points: [
        { x: -2.4, z: 4.2 },
        { x: 2.4, z: 4.2 },
        { x: 2.0, z: 6.4 },
        { x: -2.0, z: 6.4 },
        { x: 0, z: 5.0 },
      ],
      loop: true,
      speed: 0.85,
    });

    for (const [clipId, durationMs] of clips) {
      await command("pose_clip", { clip_id: clipId });
      await sleep(durationMs);
    }

    await command("action", { action: "idle", duration_ms: 0 });
    await command("move", { x: 0, z: 5.0, speed: 1.1 });
    await sleep(2600);
    await command("stop", {});
  } finally {
    button.disabled = false;
    button.dataset.playing = "false";
  }
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
