"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const player = document.querySelector("#ewp-player");
  const cues = Array.from(document.querySelectorAll(".ewp-transcript__seek"));
  if (!(player instanceof HTMLMediaElement) || cues.length === 0) return;

  let activeCue = null;

  const activate = (cue) => {
    if (activeCue === cue) return;
    if (activeCue) activeCue.removeAttribute("aria-current");
    activeCue = cue;
    if (!activeCue) return;
    activeCue.setAttribute("aria-current", "true");
    activeCue.scrollIntoView({
      block: "nearest",
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "auto"
        : "smooth",
    });
  };

  cues.forEach((cue) => {
    cue.addEventListener("click", () => {
      player.currentTime = Number(cue.dataset.startMs) / 1000;
      activate(cue);
      player.play().catch(() => {});
    });
  });

  player.addEventListener("timeupdate", () => {
    const currentMs = player.currentTime * 1000;
    const matching = cues.find(
      (cue) =>
        Number(cue.dataset.startMs) <= currentMs && currentMs < Number(cue.dataset.endMs),
    );
    activate(matching || null);
  });
});
