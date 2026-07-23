import { buildPixelGraphRaster } from "./pixel_graph_renderer.js";

self.onmessage = async (event) => {
  const { requestId, poseId, url, entry } = event.data ?? {};
  try {
    const response = await fetch(url, { cache: "force-cache" });
    if (!response.ok) throw new Error(`Pose graph ${poseId} failed: ${response.status}`);
    const graph = await response.json();
    if (
      graph.source_record_id !== entry.source_record_id ||
      (entry.graph_id && graph.graph_id !== entry.graph_id) ||
      graph.foreground_pixel_count !== entry.foreground_pixel_count
    ) {
      throw new Error(`Pose graph ${poseId} does not match its catalog entry`);
    }
    const raster = buildPixelGraphRaster(graph);
    self.postMessage(
      {
        type: "loaded",
        requestId,
        poseId,
        width: raster.width,
        height: raster.height,
        bounds: raster.bounds,
        painted: raster.painted,
        rgba: raster.rgba.buffer,
      },
      [raster.rgba.buffer],
    );
  } catch (error) {
    self.postMessage({
      type: "error",
      requestId,
      poseId,
      message: error instanceof Error ? error.message : String(error),
    });
  }
};
