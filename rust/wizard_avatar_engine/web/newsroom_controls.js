export const NEWSROOM_COMMANDS = Object.freeze([
  "anchor",
  "welcome",
  "break",
  "explain",
  "emphasize",
  "clarify",
  "compare",
  "count",
  "point",
  "reveal_graphic",
  "reveal_source",
  "handoff",
  "listen",
  "nod",
  "think",
  "react",
  "warn",
  "correct",
  "sign_off",
]);

export function newsroomCommandLabel(command) {
  return command.replaceAll("_", " ");
}

export function buildNewsroomCue({
  command,
  sequence,
  generation = 1,
  program = "general_news",
  intensity = 0.4,
  sensitivity = "normal",
  reducedMotion = false,
  durationMs = 1400,
  count = 1,
}) {
  if (!NEWSROOM_COMMANDS.includes(command)) throw new Error(`unknown newsroom command ${command}`);
  if (!Number.isInteger(sequence) || sequence < 1) throw new Error("newsroom sequence must be positive");
  if (!Number.isInteger(generation) || generation < 1) throw new Error("newsroom generation must be positive");

  const cueId = `ui-${generation}-${sequence}-${command}`;
  return {
    schema_version: "newsroom_wizard_v1",
    cue_id: cueId,
    sequence,
    program,
    command,
    target: null,
    count: command === "count" ? Math.max(1, Math.min(3, Math.round(count))) : null,
    intensity: Math.max(0, Math.min(1, Number(intensity))),
    sensitivity,
    start_ms: 0,
    duration_ms: durationMs,
    generation,
    reduced_motion: Boolean(reducedMotion),
    speech_line_id: `ui-line-${sequence}`,
    graphic_id: command === "reveal_graphic" ? `ui-graphic-${sequence}` : null,
    source_id: command === "reveal_source" ? `ui-source-${sequence}` : null,
    seed: sequence,
  };
}
