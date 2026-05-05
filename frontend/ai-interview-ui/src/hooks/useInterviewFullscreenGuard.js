import { useCallback, useEffect, useState, useRef } from "react";
import {
  clearInterviewFullscreenGuard,
  isFullscreenActive,
  isInterviewFullscreenGuardActive,
  requestInterviewFullscreen,
} from "../utils/interviewFullscreenGuard";

export function useInterviewFullscreenGuard({ enabled = true, targetRef = null, onCancel } = {}) {
  const [fullscreenBlocked, setFullscreenBlocked] = useState(false);
  const debounceTimeoutRef = useRef(null);

  const restoreFullscreen = useCallback(async () => {
    console.log("[FS-Guard] User clicked 'Resume' - restoring fullscreen");
    try {
      await requestInterviewFullscreen(targetRef?.current || document.documentElement);
      console.log("[FS-Guard] ✅ Fullscreen restored successfully");
      setFullscreenBlocked(false);
    } catch (err) {
      console.error("[FS-Guard] ❌ Failed to restore fullscreen:", err);
    }
  }, [targetRef]);

  const cancelFullscreenGuard = useCallback(() => {
    console.log("[FS-Guard] User clicked 'Cancel' - clearing guard");
    clearInterviewFullscreenGuard();
    setFullscreenBlocked(false);
    onCancel?.();
  }, [onCancel]);

  useEffect(() => {
    if (!enabled) return undefined;

    const syncFullscreenState = () => {
      const isGuardActive = isInterviewFullscreenGuardActive();
      const isCurrentlyFullscreen = isFullscreenActive();
      const isBlocked = isGuardActive && !isCurrentlyFullscreen;

      if (!isGuardActive) {
        setFullscreenBlocked(false);
        return;
      }

      // Debounce the fullscreen blocked state to avoid showing warning during page navigation
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
      
      debounceTimeoutRef.current = setTimeout(() => {
        if (isBlocked) {
          console.warn("[FS-Guard] ⚠️ FULLSCREEN EXITED - Showing warning modal");
        }
        setFullscreenBlocked(isBlocked);
      }, 500); // 500ms delay to handle navigation transitions
    };

    syncFullscreenState();
    document.addEventListener("fullscreenchange", syncFullscreenState);
    document.addEventListener("webkitfullscreenchange", syncFullscreenState);
    document.addEventListener("MSFullscreenChange", syncFullscreenState);

    return () => {
      document.removeEventListener("fullscreenchange", syncFullscreenState);
      document.removeEventListener("webkitfullscreenchange", syncFullscreenState);
      document.removeEventListener("MSFullscreenChange", syncFullscreenState);
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
    };
  }, [enabled]);

  return {
    fullscreenBlocked,
    restoreFullscreen,
    cancelFullscreenGuard,
  };
}
