import { WizardCanvas } from "./wizardCanvas.ts?v=cartoon-driver-v1";
import { WizardClient } from "./wizardClient.ts?v=cartoon-driver-v1";
import { installControls } from "./wizardControls.ts?v=cartoon-driver-v1";
import { WizardDiagnostics } from "./wizardDiagnostics.ts?v=cartoon-driver-v1";

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
