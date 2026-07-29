import { WizardCanvas } from "./wizardCanvas.ts?v=hd-alpha-v1";
import { WizardClient } from "./wizardClient.ts?v=hd-alpha-v1";
import { installControls } from "./wizardControls.ts?v=hd-alpha-v1";
import { WizardDiagnostics } from "./wizardDiagnostics.ts?v=hd-alpha-v1";

const canvas = new WizardCanvas(
  document.getElementById("wizard-canvas"),
  document.getElementById("wizard-selection"),
);
const diagnostics = new WizardDiagnostics(document.getElementById("diagnostics"));
const client = new WizardClient(canvas, diagnostics);
window.__wizardJoeCanvas = () => canvas;

function isolatedPresentationOffset(manifest, enabled) {
  if (!enabled) return 0;
  const width = Number(manifest.profile.canvas_width);
  const splitX = Number(manifest.profile.identity_split_x);
  if (
    manifest.profile.coordinate_policy !== "preserve_shared_source_canvas"
    || !Number.isInteger(width)
    || !Number.isInteger(splitX)
    || splitX <= 0
    || splitX >= width
  ) {
    return 0;
  }
  if (manifest.identity_side === "left") {
    return Math.round(width / 2 - splitX / 2);
  }
  if (manifest.identity_side === "right") {
    return Math.round(width / 2 - (splitX + width) / 2);
  }
  return 0;
}

function translateRgbaHorizontally(frame, width, height, offsetX) {
  if (!offsetX) return frame;
  const translated = new Uint8Array(frame.length);
  const sourceStartX = Math.max(0, -offsetX);
  const sourceEndX = Math.min(width, width - offsetX);
  const copyWidth = sourceEndX - sourceStartX;
  if (copyWidth <= 0) return translated;
  const destinationStartX = sourceStartX + offsetX;
  for (let y = 0; y < height; y++) {
    const sourceOffset = (y * width + sourceStartX) * 4;
    const destinationOffset = (y * width + destinationStartX) * 4;
    translated.set(
      frame.subarray(sourceOffset, sourceOffset + copyWidth * 4),
      destinationOffset,
    );
  }
  return translated;
}

async function start() {
  const params = new URLSearchParams(location.search);
  const reviewPose = params.get("hd-review");
  const reviewSequence = params.get("hd-sequence");
  if (reviewPose || reviewSequence) {
    document.body.dataset.hdReviewStep = "profile";
    const profileResponse = await fetch("/api/avatar/wizard/hd-profile", { cache: "no-store" });
    if (!profileResponse.ok) throw new Error(await profileResponse.text());
    const manifest = await profileResponse.json();
    if (!manifest.review_projection || manifest.runtime_admitted) {
      throw new Error("Invalid HD review projection contract");
    }
    const width = Number(manifest.profile.canvas_width);
    const height = Number(manifest.profile.canvas_height);
    const presentationOffsetX = isolatedPresentationOffset(
      manifest,
      params.get("hd-center-isolated") === "1",
    );
    const presentPose = (pixels) => translateRgbaHorizontally(
      pixels,
      width,
      height,
      presentationOffsetX,
    );
    document.body.classList.add("hd-review");
    document.body.dataset.hdPresentationOffsetX = String(presentationOffsetX);
    canvas.configure(width, height, "rgba");

    const loadPose = async (poseId) => {
      if (!manifest.pose_ids.includes(poseId)) throw new Error("Unknown HD review pose");
      let lastError = null;
      for (let attempt = 1; attempt <= 4; attempt++) {
        try {
          const response = await fetch(
            `/api/avatar/wizard/hd-pose/${encodeURIComponent(poseId)}`,
            { cache: "no-store" },
          );
          if (!response.ok) throw new Error(await response.text());
          const pixels = new Uint8Array(await response.arrayBuffer());
          if (pixels.length !== width * height * 4) {
            throw new Error("HD review pose size mismatch");
          }
          delete document.body.dataset.hdFrameRetry;
          return pixels;
        } catch (error) {
          lastError = error;
          document.body.dataset.hdFrameRetry = `${poseId}:${attempt}`;
          if (attempt < 4) {
            await new Promise((resolve) => setTimeout(resolve, attempt * 180));
          }
        }
      }
      throw lastError;
    };

    if (reviewSequence) {
      const sequence = manifest.sequences[reviewSequence];
      if (!sequence) throw new Error("Unknown HD review sequence");
      document.body.dataset.hdReviewStep = "load-sequence";
      let playing = true;
      let frameIndex = 0;
      let framesDrawn = 0;
      let frameFailures = 0;
      let completed = false;
      const frameInterval = 1000 / Number(sequence.fps);
      let stopped = false;
      const drawLoop = async () => {
        if (stopped) return;
        if (playing && !completed) {
          try {
            const pixels = await loadPose(sequence.pose_ids[frameIndex]);
            if (stopped) return;
            canvas.draw(presentPose(pixels));
            framesDrawn++;
            delete document.body.dataset.hdFrameError;
            const finalFrame = frameIndex === sequence.pose_ids.length - 1;
            if (finalFrame && !sequence.loop) {
              completed = true;
              playing = false;
            } else {
              frameIndex = (frameIndex + 1) % sequence.pose_ids.length;
            }
          } catch (error) {
            frameFailures++;
            document.body.dataset.hdFrameError = (
              error instanceof Error ? error.message : String(error)
            );
            setTimeout(drawLoop, Math.max(frameInterval, 500));
            return;
          }
        }
        setTimeout(drawLoop, playing ? frameInterval : 80);
      };
      await drawLoop();
      addEventListener("message", (event) => {
        if (event.origin !== location.origin || event.data?.type !== "wizard-hd-play") return;
        playing = Boolean(event.data.playing);
        if (playing && completed) {
          completed = false;
          frameIndex = 0;
        }
      });
      document.body.dataset.hdReviewStep = "ready";
      window.__wizardJoeMetrics = () => ({
        hdReview: true,
        sequenceId: reviewSequence,
        approvalState: sequence.approval_state,
        runtimeAdmitted: sequence.runtime_admitted,
        frameIndex,
        poseId: sequence.pose_ids[(frameIndex + sequence.pose_ids.length - 1) % sequence.pose_ids.length],
        framesDrawn,
        frameFailures,
        playing,
        completed,
        libraryIndexSha256: manifest.library_index_sha256,
        presentationOffsetX,
        canvas: canvas.getMetrics(),
      });
      addEventListener("pagehide", () => { stopped = true; }, { once: true });
    } else {
      const pixels = await loadPose(reviewPose);
      let opaqueSamples = 0;
      for (let offset = 3; offset < pixels.length; offset += 4100) {
        if (pixels[offset] > 0) opaqueSamples++;
      }
      document.body.dataset.hdOpaqueSamples = String(opaqueSamples);
      document.body.dataset.hdReviewStep = "project";
      canvas.draw(presentPose(pixels));
      document.body.dataset.hdReviewStep = "ready";
      window.__wizardJoeMetrics = () => ({
        hdReview: true,
        poseId: reviewPose,
        approvalState: manifest.pose_metadata[reviewPose].approval_state,
        runtimeAdmitted: manifest.pose_metadata[reviewPose].runtime_admitted,
        libraryIndexSha256: manifest.library_index_sha256,
        presentationOffsetX,
        canvas: canvas.getMetrics(),
      });
    }
    window.__wizardJoeHashes = () => [];
    return;
  }

  installControls();
  diagnostics.start();
  client.connect();
  window.__wizardJoeMetrics = () => client.getMetrics();
  window.__wizardJoeHashes = () => client.getHashHistory();
}

start().catch((error) => {
  console.error(error);
  document.body.dataset.renderError = error instanceof Error ? error.message : String(error);
});
