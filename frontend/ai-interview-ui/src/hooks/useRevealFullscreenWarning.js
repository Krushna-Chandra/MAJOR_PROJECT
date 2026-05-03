import { useEffect } from "react";

export function useRevealFullscreenWarning(active) {
  useEffect(() => {
    if (!active) return undefined;

    const timeoutId = window.setTimeout(() => {
      const warning = document.querySelector("[data-fullscreen-warning]");

      if (!warning) {
        window.scrollTo({ top: 0, left: 0, behavior: "smooth" });
        return;
      }

      warning.scrollIntoView({
        behavior: "smooth",
        block: "center",
        inline: "nearest",
      });

      if (typeof warning.focus === "function") {
        warning.focus({ preventScroll: true });
      }
    }, 50);

    return () => window.clearTimeout(timeoutId);
  }, [active]);
}
