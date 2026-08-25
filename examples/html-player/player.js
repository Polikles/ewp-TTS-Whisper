"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const player = document.querySelector("#ewp-player");
  const cues = Array.from(document.querySelectorAll(".ewp-transcript__seek"));
  const autoFollow = document.querySelector("#ewp-auto-follow");
  const theme = document.querySelector("#ewp-theme");
  if (!(player instanceof HTMLMediaElement) || cues.length === 0) return;

  let activeCue = null;

  const activate = (cue) => {
    if (activeCue === cue) return;
    if (activeCue) activeCue.removeAttribute("aria-current");
    activeCue = cue;
    if (!activeCue) return;
    activeCue.setAttribute("aria-current", "true");
    if (!(autoFollow instanceof HTMLInputElement) || autoFollow.checked) {
      activeCue.scrollIntoView({
        block: "nearest",
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "auto"
          : "smooth",
      });
    }
  };

  const metadataReady = () =>
    player.readyState >= HTMLMediaElement.HAVE_METADATA
      ? Promise.resolve()
      : new Promise((resolve) => {
          player.addEventListener("loadedmetadata", resolve, { once: true });
          player.load();
        });

  const seek = async (cue) => {
    await metadataReady();
    const targetSeconds = Number(cue.dataset.startMs) / 1000;
    const seeked = new Promise((resolve) =>
      player.addEventListener("seeked", resolve, { once: true }),
    );
    player.currentTime = targetSeconds;
    activate(cue);
    await Promise.race([seeked, new Promise((resolve) => setTimeout(resolve, 750))]);
    await player.play();
  };

  cues.forEach((cue) => {
    cue.addEventListener("click", () => {
      seek(cue).catch(() => {});
    });
  });

  if (theme instanceof HTMLSelectElement) {
    theme.addEventListener("change", () => {
      if (theme.value === "system") document.documentElement.removeAttribute("data-theme");
      else document.documentElement.dataset.theme = theme.value;
    });
  }

  player.addEventListener("timeupdate", () => {
    const currentMs = player.currentTime * 1000;
    const matching = cues.find(
      (cue) =>
        Number(cue.dataset.startMs) <= currentMs && currentMs < Number(cue.dataset.endMs),
    );
    activate(matching || null);
  });
});
