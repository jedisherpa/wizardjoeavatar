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
    document.body.classList.add("hd-review");
    canvas.configure(width, height, "rgba");

    const loadPose = async (poseId) => {
      if (!manifest.pose_ids.includes(poseId)) throw new Error("Unknown HD review pose");
      const response = await fetch(`/api/avatar/wizard/hd-pose/${encodeURIComponent(poseId)}`, {
        cache: "no-store",
      });
      if (!response.ok) throw new Error(await response.text());
      const pixels = new Uint8Array(await response.arrayBuffer());
      if (pixels.length !== width * height * 4) throw new Error("HD review pose size mismatch");
      return pixels;
    };

    if (reviewSequence) {
      const sequence = manifest.sequences[reviewSequence];
      if (!sequence) throw new Error("Unknown HD review sequence");
      document.body.dataset.hdReviewStep = "load-sequence";
      let playing = true;
      let frameIndex = 0;
      let framesDrawn = 0;
      const frameInterval = 1000 / Number(sequence.fps);
      let stopped = false;
      const drawLoop = async () => {
        if (playing) {
          const pixels = await loadPose(sequence.pose_ids[frameIndex]);
          if (stopped) return;
          canvas.draw(pixels);
          frameIndex = (frameIndex + 1) % sequence.pose_ids.length;
          framesDrawn++;
        }
        setTimeout(drawLoop, playing ? frameInterval : 80);
      };
      await drawLoop();
      addEventListener("message", (event) => {
        if (event.origin !== location.origin || event.data?.type !== "wizard-hd-play") return;
        playing = Boolean(event.data.playing);
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
        playing,
        libraryIndexSha256: manifest.library_index_sha256,
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
      canvas.draw(pixels);
      document.body.dataset.hdReviewStep = "ready";
      window.__wizardJoeMetrics = () => ({
        hdReview: true,
        poseId: reviewPose,
        approvalState: manifest.pose_metadata[reviewPose].approval_state,
        runtimeAdmitted: manifest.pose_metadata[reviewPose].runtime_admitted,
        libraryIndexSha256: manifest.library_index_sha256,
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
