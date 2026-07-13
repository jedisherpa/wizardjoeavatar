import { WizardCanvas } from "./wizardCanvas.ts?v=animation-demo";
import { WizardClient } from "./wizardClient.ts?v=animation-demo";
import { installControls } from "./wizardControls.ts?v=animation-demo";
import { WizardDiagnostics } from "./wizardDiagnostics.ts?v=animation-demo";

const canvas = new WizardCanvas(
  document.getElementById("wizard-canvas"),
  document.getElementById("wizard-selection"),
);
const diagnostics = new WizardDiagnostics(document.getElementById("diagnostics"));
const client = new WizardClient(canvas, diagnostics);

installControls();
diagnostics.start();
client.connect();

window.__wizardJoeMetrics = () => client.getMetrics();
window.__wizardJoeHashes = () => client.getHashHistory();
window.__wizardJoeCanvas = () => canvas;
