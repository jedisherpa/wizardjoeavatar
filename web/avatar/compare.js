const livePlayer = document.getElementById("live-player");
const hdPlayer = document.getElementById("hd-player");

document.getElementById("play-both").addEventListener("click", () => {
  const play = livePlayer.contentDocument?.querySelector('button[aria-label="Play demo"]');
  play?.click();
  hdPlayer.contentWindow?.postMessage({ type: "wizard-hd-play", playing: true }, location.origin);
});

document.getElementById("pause-hd").addEventListener("click", () => {
  hdPlayer.contentWindow?.postMessage({ type: "wizard-hd-play", playing: false }, location.origin);
});

document.getElementById("restart").addEventListener("click", () => {
  livePlayer.contentWindow?.location.reload();
  hdPlayer.contentWindow?.location.reload();
});
