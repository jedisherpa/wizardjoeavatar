import { WizardCanvas } from "./wizardCanvas.ts?v=character-director-v2";
import { WizardClient } from "./wizardClient.ts?v=character-director-v2";
import { installControls } from "./wizardControls.ts?v=character-director-v2";
import { WizardDiagnostics } from "./wizardDiagnostics.ts?v=character-director-v2";

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
