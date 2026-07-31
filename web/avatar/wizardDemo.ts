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

function blendRgbaFrames(first, second, blendMilli) {
  if (!second || blendMilli <= 0) return first;
  if (blendMilli >= 1000) return second;
  const result = new Uint8Array(first.length);
  const inverse = 1000 - blendMilli;
  for (let index = 0; index < first.length; index++) {
    result[index] = Math.round(
      (first[index] * inverse + second[index] * blendMilli) / 1000,
    );
  }
  return result;
}

function opaqueBoundsRgba(frame, width, height) {
  let minX = width;
  let minY = height;
  let maxX = -1;
  let maxY = -1;
  for (let y = 0; y < height; y++) {
    const rowOffset = y * width * 4;
    for (let x = 0; x < width; x++) {
      if (frame[rowOffset + x * 4 + 3] === 0) continue;
      minX = Math.min(minX, x);
      minY = Math.min(minY, y);
      maxX = Math.max(maxX, x);
      maxY = Math.max(maxY, y);
    }
  }
  return maxX >= minX && maxY >= minY
    ? { minX, minY, maxX, maxY }
    : null;
}

function unionBounds(first, second) {
  if (!first) return second;
  if (!second) return first;
  return {
    minX: Math.min(first.minX, second.minX),
    minY: Math.min(first.minY, second.minY),
    maxX: Math.max(first.maxX, second.maxX),
    maxY: Math.max(first.maxY, second.maxY),
  };
}

function fitPairReviewPresentation(canvasElement, bounds, sourceWidth, sourceHeight) {
  if (!bounds) return null;
  const topInset = 54;
  const margin = 18;
  const cssWidth = Number.parseFloat(canvasElement.style.width) || sourceWidth;
  const cssHeight = Number.parseFloat(canvasElement.style.height) || sourceHeight;
  const sourceScaleX = cssWidth / sourceWidth;
  const sourceScaleY = cssHeight / sourceHeight;
  const boundsWidth = (bounds.maxX - bounds.minX + 1) * sourceScaleX;
  const boundsHeight = (bounds.maxY - bounds.minY + 1) * sourceScaleY;
  const availableWidth = Math.max(1, window.innerWidth - margin * 2);
  const availableHeight = Math.max(1, window.innerHeight - topInset - margin * 2);
  const presentationScale = Math.max(
    1,
    Math.min(availableWidth / boundsWidth, availableHeight / boundsHeight),
  );
  const centerX = ((bounds.minX + bounds.maxX + 1) / 2) * sourceScaleX;
  const centerY = ((bounds.minY + bounds.maxY + 1) / 2) * sourceScaleY;
  const translateX = window.innerWidth / 2 - centerX * presentationScale;
  const translateY = availableHeight / 2 + margin - centerY * presentationScale;

  canvasElement.style.position = "fixed";
  canvasElement.style.left = "0";
  canvasElement.style.top = `${topInset}px`;
  canvasElement.style.transformOrigin = "0 0";
  canvasElement.style.transform = (
    `matrix(${presentationScale}, 0, 0, ${presentationScale}, ${translateX}, ${translateY})`
  );
  return {
    bounds,
    presentationScale,
    translateX,
    translateY,
  };
}

async function start() {
  const params = new URLSearchParams(location.search);
  const reviewPose = params.get("hd-review");
  const pairReviewSequence = params.get("hd-pair-review");
  const reviewSequence = pairReviewSequence || params.get("hd-sequence");
  const reviewPerformance = params.get("hd-performance") === "1";
  if (reviewPose || reviewSequence || reviewPerformance) {
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
    const poseCache = new Map();

    const loadPose = async (poseId) => {
      if (!manifest.pose_ids.includes(poseId)) throw new Error("Unknown HD review pose");
      if (poseCache.has(poseId)) return poseCache.get(poseId);
      const loading = (async () => {
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
      })();
      poseCache.set(poseId, loading);
      try {
        return await loading;
      } catch (error) {
        poseCache.delete(poseId);
        throw error;
      }
    };

    if (reviewPerformance) {
      const canvasElement = document.getElementById("wizard-canvas");
      const requestedOrigin = params.get("controller-origin");
      const controllerOrigin = requestedOrigin
        ? new URL(requestedOrigin).origin
        : location.origin;
      let poseId = "013_idle_warm_camera_ready";
      let nextPoseId = null;
      let blendMilli = 0;
      let scaleMilli = 1000;
      let offsetXPx = 0;
      let offsetYPx = 0;
      let mediaPositionMs = 0;
      let framesDrawn = 0;
      let frameFailures = 0;
      let requestGeneration = 0;

      const presentFrame = async (message) => {
        const generation = ++requestGeneration;
        poseId = String(message.poseId || poseId);
        nextPoseId = message.nextPoseId ? String(message.nextPoseId) : null;
        blendMilli = Math.max(0, Math.min(1000, Number(message.blendMilli) || 0));
        scaleMilli = Math.max(200, Math.min(1200, Number(message.scaleMilli) || 1000));
        offsetXPx = Math.max(-80, Math.min(80, Number(message.offsetXPx) || 0));
        offsetYPx = Math.max(-80, Math.min(80, Number(message.offsetYPx) || 0));
        mediaPositionMs = Math.max(0, Number(message.mediaPositionMs) || 0);
        try {
          const first = await loadPose(poseId);
          const second = nextPoseId ? await loadPose(nextPoseId) : null;
          if (generation !== requestGeneration) return;
          canvas.draw(
            presentPose(blendRgbaFrames(first, second, blendMilli)),
          );
          canvasElement.style.transformOrigin = "50% 82%";
          canvasElement.style.transform = (
            `translate(${offsetXPx}px, ${offsetYPx}px) scale(${scaleMilli / 1000})`
          );
          framesDrawn++;
          delete document.body.dataset.hdFrameError;
        } catch (error) {
          frameFailures++;
          document.body.dataset.hdFrameError = (
            error instanceof Error ? error.message : String(error)
          );
        }
      };

      addEventListener("message", (event) => {
        if (
          event.source !== parent
          || event.origin !== controllerOrigin
          || event.data?.type !== "wizard-hd-performance-frame"
        ) return;
        void presentFrame(event.data);
      });
      await presentFrame({ poseId });
      document.body.dataset.hdReviewStep = "ready";
      window.__wizardJoeMetrics = () => ({
        hdReview: true,
        performanceReview: true,
        poseId,
        nextPoseId,
        blendMilli,
        scaleMilli,
        offsetXPx,
        offsetYPx,
        mediaPositionMs,
        framesDrawn,
        frameFailures,
        libraryIndexSha256: manifest.library_index_sha256,
        canvas: canvas.getMetrics(),
      });
      parent.postMessage(
        { type: "wizard-hd-performance-ready" },
        controllerOrigin,
      );
    } else if (pairReviewSequence) {
      const sequence = manifest.sequences[pairReviewSequence];
      if (!sequence) throw new Error("Unknown HD pair-review sequence");
      if (
        !Array.isArray(sequence.pose_ids)
        || sequence.pose_ids.length < 2
        || sequence.pose_ids.length % 2 !== 0
      ) {
        throw new Error("HD pair-review sequence must contain closed/open pairs");
      }
      document.body.classList.add("hd-pair-review");
      document.body.dataset.hdReviewStep = "load-pair";
      const canvasElement = document.getElementById("wizard-canvas");
      const pairCount = sequence.pose_ids.length / 2;
      const requestedPair = Number.parseInt(params.get("pair") || "1", 10);
      let pairIndex = Number.isInteger(requestedPair)
        ? Math.max(0, Math.min(pairCount - 1, requestedPair - 1))
        : 0;
      let stateIndex = 0;
      let playing = false;
      let framesDrawn = 0;
      let frameFailures = 0;
      let stopped = false;
      let playbackTimer = null;
      let pairFrames = null;
      let pairPresentation = null;

      const controls = document.createElement("section");
      controls.className = "hd-pair-review-controls";
      controls.setAttribute("aria-label", "Closed and open pose pair review");
      controls.innerHTML = `
        <button type="button" data-pair-previous title="Previous pair" aria-label="Previous pair">←</button>
        <button type="button" data-pair-closed title="Show closed pose" aria-label="Show closed pose">■</button>
        <button type="button" data-pair-play title="Play pair" aria-label="Play pair" aria-pressed="false">▶</button>
        <button type="button" data-pair-open title="Show open pose" aria-label="Show open pose">◇</button>
        <button type="button" data-pair-next title="Next pair" aria-label="Next pair">→</button>
        <output data-pair-label aria-live="polite"></output>
      `;
      document.querySelector(".stage-shell").append(controls);
      const label = controls.querySelector("[data-pair-label]");
      const playButton = controls.querySelector("[data-pair-play]");

      const pairPoseId = () => sequence.pose_ids[pairIndex * 2 + stateIndex];
      const loadPairFrames = async () => {
        const closedPoseId = sequence.pose_ids[pairIndex * 2];
        const openPoseId = sequence.pose_ids[pairIndex * 2 + 1];
        const [closedFrame, openFrame] = await Promise.all([
          loadPose(closedPoseId),
          loadPose(openPoseId),
        ]);
        const pairBounds = unionBounds(
          opaqueBoundsRgba(closedFrame, width, height),
          opaqueBoundsRgba(openFrame, width, height),
        );
        pairFrames = [closedFrame, openFrame];
        pairPresentation = fitPairReviewPresentation(
          canvasElement,
          pairBounds,
          width,
          height,
        );
      };
      const readablePairName = () => {
        const closedPose = sequence.pose_ids[pairIndex * 2];
        return closedPose
          .replace(/^.*?act\.\d+\./, "")
          .replace(/[._-]+/g, " ");
      };
      const updateControls = () => {
        label.textContent = `${pairIndex + 1} / ${pairCount} · ${readablePairName()} · ${stateIndex ? "open" : "closed"}`;
        document.body.dataset.hdPairReview = pairReviewSequence;
        document.body.dataset.hdPairNumber = String(pairIndex + 1);
        document.body.dataset.hdPairState = stateIndex ? "open" : "closed";
        document.body.dataset.hdPairPlaying = String(playing);
        playButton.textContent = playing ? "❚❚" : "▶";
        playButton.title = playing ? "Pause pair" : "Play pair";
        playButton.setAttribute("aria-label", playButton.title);
        playButton.setAttribute("aria-pressed", String(playing));
        controls.querySelector("[data-pair-closed]").setAttribute(
          "aria-pressed",
          String(stateIndex === 0),
        );
        controls.querySelector("[data-pair-open]").setAttribute(
          "aria-pressed",
          String(stateIndex === 1),
        );
      };
      const drawPairState = async () => {
        try {
          if (!pairFrames) await loadPairFrames();
          const pixels = pairFrames[stateIndex];
          if (stopped) return;
          canvas.draw(presentPose(pixels));
          framesDrawn++;
          delete document.body.dataset.hdFrameError;
        } catch (error) {
          frameFailures++;
          document.body.dataset.hdFrameError = (
            error instanceof Error ? error.message : String(error)
          );
        }
        updateControls();
      };
      const schedulePlayback = () => {
        clearTimeout(playbackTimer);
        if (!playing || stopped) return;
        playbackTimer = setTimeout(async () => {
          stateIndex = stateIndex ? 0 : 1;
          await drawPairState();
          schedulePlayback();
        }, 650);
      };
      const setPlaying = (nextPlaying) => {
        playing = Boolean(nextPlaying);
        updateControls();
        schedulePlayback();
      };
      const selectPair = async (nextPairIndex) => {
        setPlaying(false);
        pairIndex = (nextPairIndex + pairCount) % pairCount;
        stateIndex = 0;
        pairFrames = null;
        const url = new URL(location.href);
        url.searchParams.set("pair", String(pairIndex + 1));
        history.replaceState(null, "", url);
        await drawPairState();
      };

      controls.querySelector("[data-pair-previous]").addEventListener(
        "click",
        () => void selectPair(pairIndex - 1),
      );
      controls.querySelector("[data-pair-next]").addEventListener(
        "click",
        () => void selectPair(pairIndex + 1),
      );
      controls.querySelector("[data-pair-closed]").addEventListener(
        "click",
        () => {
          setPlaying(false);
          stateIndex = 0;
          void drawPairState();
        },
      );
      controls.querySelector("[data-pair-open]").addEventListener(
        "click",
        () => {
          setPlaying(false);
          stateIndex = 1;
          void drawPairState();
        },
      );
      playButton.addEventListener("click", () => setPlaying(!playing));
      addEventListener("keydown", (event) => {
        if (event.key === "ArrowLeft") void selectPair(pairIndex - 1);
        if (event.key === "ArrowRight") void selectPair(pairIndex + 1);
        if (event.key === " ") {
          event.preventDefault();
          setPlaying(!playing);
        }
      });
      await drawPairState();
      window.__wizardJoeMetrics = () => ({
        hdReview: true,
        pairReview: true,
        sequenceId: pairReviewSequence,
        approvalState: sequence.approval_state,
        runtimeAdmitted: sequence.runtime_admitted,
        pairIndex,
        pairNumber: pairIndex + 1,
        pairCount,
        state: stateIndex ? "open" : "closed",
        poseId: pairPoseId(),
        framesDrawn,
        frameFailures,
        playing,
        libraryIndexSha256: manifest.library_index_sha256,
        presentationOffsetX,
        pairPresentation,
        canvas: canvas.getMetrics(),
      });
      document.body.dataset.hdReviewStep = "ready";
      addEventListener("resize", () => {
        if (pairPresentation?.bounds) {
          pairPresentation = fitPairReviewPresentation(
            canvasElement,
            pairPresentation.bounds,
            width,
            height,
          );
        }
      });
      addEventListener(
        "pagehide",
        () => {
          stopped = true;
          clearTimeout(playbackTimer);
        },
        { once: true },
      );
    } else if (reviewSequence) {
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
