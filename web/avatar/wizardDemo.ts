import { WizardCanvas } from "./wizardCanvas.ts?v=cartoon-driver-v1";
import { WizardClient } from "./wizardClient.ts?v=cartoon-driver-v1";
import { installControls } from "./wizardControls.ts?v=cartoon-driver-v1";
import { WizardDiagnostics } from "./wizardDiagnostics.ts?v=cartoon-driver-v1";
import { activeCharacterId } from "./wizardClient.ts?v=cartoon-driver-v1";

const canvas = new WizardCanvas(
  document.getElementById("wizard-canvas"),
  document.getElementById("wizard-selection"),
);
const diagnostics = new WizardDiagnostics(document.getElementById("diagnostics"));
const client = new WizardClient(canvas, diagnostics);

async function installCharacterSelector() {
  const select = document.getElementById("character-select");
  if (!select) return;
  const response = await fetch("/api/avatar/characters");
  const payload = await response.json();
  payload.characters.forEach((character) => {
    const option = document.createElement("option");
    option.value = character.character_id;
    option.textContent = character.display_name;
    option.selected = character.character_id === activeCharacterId;
    select.append(option);
  });
  select.addEventListener("change", () => {
    const url = new URL(location.href);
    url.searchParams.set("character", select.value);
    location.assign(url);
  });
}

installControls();
installCharacterSelector().catch(console.error);
diagnostics.start();
client.connect();

window.__wizardJoeMetrics = () => client.getMetrics();
window.__wizardJoeHashes = () => client.getHashHistory();
window.__wizardJoeCanvas = () => canvas;
