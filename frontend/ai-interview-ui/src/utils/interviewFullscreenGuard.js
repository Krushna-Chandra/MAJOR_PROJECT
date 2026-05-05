const INTERVIEW_FULLSCREEN_GUARD_KEY = "interviewFullscreenGuardActive";

export const isFullscreenActive = () => {
  const active = Boolean(
    document.fullscreenElement ||
      document.webkitFullscreenElement ||
      document.msFullscreenElement
  );
  return active;
};

export const activateInterviewFullscreenGuard = () => {
  console.log("[FS-Util] Activating fullscreen guard");
  sessionStorage.setItem(INTERVIEW_FULLSCREEN_GUARD_KEY, "true");
};

export const clearInterviewFullscreenGuard = () => {
  console.log("[FS-Util] Clearing fullscreen guard");
  sessionStorage.removeItem(INTERVIEW_FULLSCREEN_GUARD_KEY);
};

export const isInterviewFullscreenGuardActive = () => {
  const active = sessionStorage.getItem(INTERVIEW_FULLSCREEN_GUARD_KEY) === "true";
  return active;
};

export const requestInterviewFullscreen = async (target = document.documentElement) => {
  console.log("[FS-Util] Requesting fullscreen...");
  
  if (isFullscreenActive()) {
    console.log("[FS-Util] Already in fullscreen, just activating guard");
    activateInterviewFullscreenGuard();
    return true;
  }

  const fullscreenTarget = target || document.documentElement;
  const requestFullscreen =
    fullscreenTarget.requestFullscreen ||
    fullscreenTarget.webkitRequestFullscreen ||
    fullscreenTarget.mozRequestFullScreen;

  if (!requestFullscreen) {
    console.error("[FS-Util] Fullscreen API not supported in this browser");
    throw new Error("Fullscreen mode is not supported in this browser.");
  }

  try {
    await requestFullscreen.call(fullscreenTarget);

    if (!isFullscreenActive()) {
      console.error("[FS-Util] Fullscreen request was not fulfilled");
      throw new Error("Fullscreen did not start. Please try again.");
    }

    console.log("[FS-Util] ✅ Fullscreen active - guard activated");
    activateInterviewFullscreenGuard();
    return true;
  } catch (err) {
    console.error("[FS-Util] ❌ Error requesting fullscreen:", err);
    throw err;
  }
};
