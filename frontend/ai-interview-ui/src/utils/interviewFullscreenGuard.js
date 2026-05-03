const INTERVIEW_FULLSCREEN_GUARD_KEY = "interviewFullscreenGuardActive";

export const isFullscreenActive = () =>
  Boolean(
    document.fullscreenElement ||
      document.webkitFullscreenElement ||
      document.msFullscreenElement
  );

export const activateInterviewFullscreenGuard = () => {
  sessionStorage.setItem(INTERVIEW_FULLSCREEN_GUARD_KEY, "true");
};

export const clearInterviewFullscreenGuard = () => {
  sessionStorage.removeItem(INTERVIEW_FULLSCREEN_GUARD_KEY);
};

export const isInterviewFullscreenGuardActive = () =>
  sessionStorage.getItem(INTERVIEW_FULLSCREEN_GUARD_KEY) === "true";

export const requestInterviewFullscreen = async (target = document.documentElement) => {
  if (isFullscreenActive()) {
    activateInterviewFullscreenGuard();
    return true;
  }

  const fullscreenTarget = target || document.documentElement;
  const requestFullscreen =
    fullscreenTarget.requestFullscreen ||
    fullscreenTarget.webkitRequestFullscreen ||
    fullscreenTarget.msRequestFullscreen;

  if (!requestFullscreen) {
    throw new Error("Fullscreen mode is not supported in this browser.");
  }

  await requestFullscreen.call(fullscreenTarget);

  if (!isFullscreenActive()) {
    throw new Error("Fullscreen did not start. Please try again.");
  }

  activateInterviewFullscreenGuard();
  return true;
};
