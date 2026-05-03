import { useCallback, useEffect, useState } from "react";
import {
  clearInterviewFullscreenGuard,
  isFullscreenActive,
  isInterviewFullscreenGuardActive,
  requestInterviewFullscreen,
} from "../utils/interviewFullscreenGuard";

export function useInterviewFullscreenGuard({ enabled = true, targetRef = null, onCancel } = {}) {
  const [fullscreenBlocked, setFullscreenBlocked] = useState(
    () => enabled && isInterviewFullscreenGuardActive() && !isFullscreenActive()
  );

  const restoreFullscreen = useCallback(async () => {
    await requestInterviewFullscreen(targetRef?.current || document.documentElement);
    setFullscreenBlocked(false);
  }, [targetRef]);

  const cancelFullscreenGuard = useCallback(() => {
    clearInterviewFullscreenGuard();
    setFullscreenBlocked(false);
    onCancel?.();
  }, [onCancel]);

  useEffect(() => {
    if (!enabled) return undefined;

    const syncFullscreenState = () => {
      if (!isInterviewFullscreenGuardActive()) {
        setFullscreenBlocked(false);
        return;
      }

      setFullscreenBlocked(!isFullscreenActive());
    };

    syncFullscreenState();
    document.addEventListener("fullscreenchange", syncFullscreenState);
    document.addEventListener("webkitfullscreenchange", syncFullscreenState);
    document.addEventListener("MSFullscreenChange", syncFullscreenState);

    return () => {
      document.removeEventListener("fullscreenchange", syncFullscreenState);
      document.removeEventListener("webkitfullscreenchange", syncFullscreenState);
      document.removeEventListener("MSFullscreenChange", syncFullscreenState);
    };
  }, [enabled]);

  return {
    fullscreenBlocked,
    restoreFullscreen,
    cancelFullscreenGuard,
  };
}
