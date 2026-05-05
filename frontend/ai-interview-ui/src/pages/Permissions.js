import React, { useState, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import "../App.css";
import { useScrollToTop } from "../hooks/useScrollToTop";
import {
  clearInterviewFullscreenGuard,
  isFullscreenActive,
  requestInterviewFullscreen,
} from "../utils/interviewFullscreenGuard";
import { useInterviewFullscreenGuard } from "../hooks/useInterviewFullscreenGuard";

// vector icons (simple, professional)
const CameraIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
    <path d="M12 9a3 3 0 100 6 3 3 0 000-6z" />
    <path d="M4 7h4l2-2h4l2 2h4a2 2 0 012 2v10a2 2 0 01-2 2H4a2 2 0 01-2-2V9a2 2 0 012-2z" />
  </svg>
);

const MicIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
    <path d="M12 14a3 3 0 003-3V5a3 3 0 10-6 0v6a3 3 0 003 3z" />
    <path d="M19 11a1 1 0 00-2 0 5 5 0 01-10 0 1 1 0 00-2 0 7 7 0 006 6.92V21h2v-3.08A7 7 0 0019 11z" />
  </svg>
);

const BrowserIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <line x1="2" y1="12" x2="22" y2="12" />
    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
  </svg>
);

const FullscreenIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
  </svg>
);

function Permissions() {
  useScrollToTop();
  const navigate = useNavigate();
  const location = useLocation();
  const videoRef = useRef(null);
  const permissionsPageRef = useRef(null);
  const [permissions, setPermissions] = useState({
    camera: false,
    microphone: false,
    browser: false,
    fullscreen: false
  });
  const [deniedPerm, setDeniedPerm] = useState({
    camera: false,
    microphone: false,
    browser: false,
    fullscreen: false
  });
  // loading state per permission so we can show cursor/spinner
  const [loadingPerm, setLoadingPerm] = useState({
    camera: false,
    microphone: false,
    browser: false,
    fullscreen: false
  });
  const [audioDb, setAudioDb] = useState(-Infinity);
  const [browserName, setBrowserName] = useState("");
  const [showFullscreenModal, setShowFullscreenModal] = useState(false);
  const micStreamRef = useRef(null);

  // Fullscreen guard hook - shows warning if user exits fullscreen
  const handleCancelFullscreen = () => {
    clearInterviewFullscreenGuard();
    navigate("/", { replace: true });
  };

  const { fullscreenBlocked, restoreFullscreen, cancelFullscreenGuard } =
    useInterviewFullscreenGuard({ onCancel: handleCancelFullscreen });
  // Don't show warning on Permissions page - only track fullscreen state
  // useRevealFullscreenWarning(fullscreenBlocked);

  const resetPermissionsState = () => {
    setPermissions({ camera: false, microphone: false, browser: false, fullscreen: false });
    setDeniedPerm({ camera: false, microphone: false, browser: false, fullscreen: false });
    setLoadingPerm({ camera: false, microphone: false, browser: false, fullscreen: false });
    setBrowserName("");
    setAudioDb(-Infinity);
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((t) => t.stop());
      micStreamRef.current = null;
    }
    if (cameraStreamRef.current) {
      cameraStreamRef.current.getTracks().forEach((t) => t.stop());
      cameraStreamRef.current = null;
    }
  };

  // when microphone permission granted, start capturing level
  React.useEffect(() => {
    if (!permissions.microphone) return;
    (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        micStreamRef.current = stream;
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const analyser = audioCtx.createAnalyser();
        const source = audioCtx.createMediaStreamSource(stream);
        source.connect(analyser);
        analyser.fftSize = 256;
        const data = new Uint8Array(analyser.frequencyBinCount);
        const tick = () => {
          analyser.getByteFrequencyData(data);
          let values = 0;
          for (let i = 0; i < data.length; i++) values += data[i];
          const average = values / data.length / 255; // 0..1
          const db = 20 * Math.log10(average + 1e-6); // negative dB
          setAudioDb(db);
          requestAnimationFrame(tick);
        };
        tick();
      } catch {}
    })();
    return () => {
      micStreamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, [permissions.microphone]);
  const cameraStreamRef = useRef(null);

  // reset each time page opens
  React.useEffect(() => {
    resetPermissionsState();

    return () => {
      resetPermissionsState();
    };
  }, []);

  // helper to detect permanent denials and inform the user
  const checkPermissionStatus = async (name) => {
    if (navigator.permissions) {
      try {
        const p = await navigator.permissions.query({ name });
        if (p.state === "denied") {
          // browser won't show prompt again
          alert(
            `The ${name} permission has been blocked in your browser. ` +
              `Please enable it via the site settings (click the lock icon near the address bar) and retry.`
          );
          return false;
        }
      } catch {}
    }
    return true;
  };

  const requestCamera = async () => {
    // if the camera permission is already denied by browser settings, bail out early
    if (!(await checkPermissionStatus("camera"))) {
      setDeniedPerm((d) => ({ ...d, camera: true }));
      return;
    }

    setLoadingPerm((l) => ({ ...l, camera: true }));
    setDeniedPerm((d) => ({ ...d, camera: false }));
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      stream.getTracks().forEach((t) => t.stop());
      setPermissions((p) => ({ ...p, camera: true }));
    } catch (err) {
      setDeniedPerm((d) => ({ ...d, camera: true }));
      // silent; state and UI already indicate denial
    } finally {
      setLoadingPerm((l) => ({ ...l, camera: false }));
    }
  };

  const requestMicrophone = async () => {
    if (!(await checkPermissionStatus("microphone"))) {
      setDeniedPerm((d) => ({ ...d, microphone: true }));
      return;
    }

    setLoadingPerm((l) => ({ ...l, microphone: true }));
    setDeniedPerm((d) => ({ ...d, microphone: false }));
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((t) => t.stop());
      setPermissions((p) => ({ ...p, microphone: true }));
    } catch (err) {
      setDeniedPerm((d) => ({ ...d, microphone: true }));
    } finally {
      setLoadingPerm((l) => ({ ...l, microphone: false }));
    }
  };

  // navigation helpers for footer buttons
  const goHome = () => {
    resetPermissionsState();
    navigate("/");
  };
  const goBack = () => {
    resetPermissionsState();
    navigate(-1);
  };

  const detectBrowser = () => {
    setLoadingPerm((l) => ({ ...l, browser: true }));
    setDeniedPerm((d) => ({ ...d, browser: false }));
    
    setTimeout(() => {
      const userAgent = navigator.userAgent;
      let detected = "Unknown";
      
      if (userAgent.indexOf("Firefox") > -1) {
        detected = "Firefox";
      } else if (userAgent.indexOf("Chrome") > -1 && userAgent.indexOf("Chromium") === -1) {
        detected = "Chrome";
      } else if (userAgent.indexOf("Safari") > -1 && userAgent.indexOf("Chrome") === -1) {
        detected = "Safari";
      } else if (userAgent.indexOf("Edge") > -1 || userAgent.indexOf("Edg") > -1) {
        detected = "Edge";
      } else if (userAgent.indexOf("Opera") > -1 || userAgent.indexOf("OPR") > -1) {
        detected = "Opera";
      } else if (userAgent.indexOf("Chromium") > -1) {
        detected = "Chromium";
      }
      
      setBrowserName(detected);
      setPermissions((p) => ({ ...p, browser: true }));
      setLoadingPerm((l) => ({ ...l, browser: false }));
    }, 500);
  };

  const requestFullscreen = () => {
    setShowFullscreenModal(true);
  };

  const enterFullscreenMode = async () => {
    console.log("[Permissions] User clicked 'Enter Fullscreen' button");
    setShowFullscreenModal(false);
    setLoadingPerm((l) => ({ ...l, fullscreen: true }));
    setDeniedPerm((d) => ({ ...d, fullscreen: false }));
    try {
      console.log("[Permissions] Requesting fullscreen API...");
      await requestInterviewFullscreen(document.documentElement);
      console.log("[Permissions] ✅ Fullscreen entered successfully");
      console.log("[Permissions] Fullscreen guard activated");
      setPermissions((p) => ({ ...p, fullscreen: true }));
    } catch (err) {
      console.error("[Permissions] ❌ Failed to enter fullscreen:", err);
      setDeniedPerm((d) => ({ ...d, fullscreen: true }));
    } finally {
      setLoadingPerm((l) => ({ ...l, fullscreen: false }));
    }
  };

  const cancelFullscreen = () => {
    setShowFullscreenModal(false);
  };

  const goProceed = async () => {
    if (allPermissionsGranted) {
      if (fullscreenBlocked || !isFullscreenActive()) {
        await restoreFullscreen();
      }

      if (!isFullscreenActive()) {
        setDeniedPerm((d) => ({ ...d, fullscreen: true }));
        return;
      }
      
      if (location.state?.fromInstructions) {
        navigate("/interview", {
          state: {
            ...(location.state || {}),
            permissionChecked: true,
          },
        });
        return;
      }
      navigate("/instructions", {
        state: {
          ...(location.state || {}),
          permissionChecked: true,
        },
      });
    }
  };

  const allPermissionsGranted = permissions.camera && permissions.microphone && permissions.browser && permissions.fullscreen;

  // change cursor to wait when any permission is loading
  React.useEffect(() => {
    const anyLoading = Object.values(loadingPerm).some(Boolean);
    document.body.style.cursor = anyLoading ? "wait" : "default";
  }, [loadingPerm]);

  // compute audio bar color based on level
  const getAudioColor = (db) => {
    // use dB thresholds
    if (db < -18) return "#ef4444"; // too low
    if (db < -12) return "#facc15"; // okay
    if (db < -6) return "#10b981"; // good
    return "#059669"; // very loud
  };

  // camera preview when permission given
  React.useEffect(() => {
    if (permissions.camera) {
      (async () => {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ video: true });
          cameraStreamRef.current = stream;
          if (videoRef.current) {
            videoRef.current.srcObject = stream;
            videoRef.current.muted = true;
            videoRef.current.playsInline = true;
            await videoRef.current.play();
          }
        } catch {};
      })();
    }

    return () => {
      if (cameraStreamRef.current) {
        cameraStreamRef.current.getTracks().forEach((t) => t.stop());
        cameraStreamRef.current = null;
      }
    };
  }, [permissions.camera]);

  // gather some system info for the right panel
  const [sysInfo, setSysInfo] = useState({
    os: navigator.platform || "Unknown",
    browser: "Browser",
    dimension: `${window.innerWidth} x ${window.innerHeight}`,
    screen: `${window.screen.width} x ${window.screen.height}`,
    cookies: navigator.cookieEnabled ? "Enabled" : "Disabled",
    popup: "Enabled",
    download: "-- Mbps",
    upload: "-- Mbps",
    time: new Date().toLocaleTimeString()
  });

  React.useEffect(() => {
    if (browserName) {
      setSysInfo((prev) => ({ ...prev, browser: browserName }));
    }
  }, [browserName]);

  React.useEffect(() => {
    const measureSpeed = async () => {
      try {
        const start = Date.now();
        const resp = await fetch("https://via.placeholder.com/100?" + Math.random());
        const blob = await resp.blob();
        const duration = (Date.now() - start) / 1000;
        const bits = blob.size * 8;
        const mbps = (bits / duration / (1024 * 1024)).toFixed(2);
        setSysInfo((s) => ({ ...s, download: `${mbps} Mbps` }));
      } catch {}
    };

    const measureUpload = async () => {
      try {
        // send a blob of ~200KB to measure upload
        const size = 200 * 1024; // 200KB
        const data = new Uint8Array(size);
        window.crypto.getRandomValues(data);
        const blob = new Blob([data]);
        const start = Date.now();
        await fetch("https://jsonplaceholder.typicode.com/posts", {
          method: "POST",
          body: blob,
          headers: { "Content-Type": "application/octet-stream" }
        });
        const duration = (Date.now() - start) / 1000;
        const bits = blob.size * 8;
        const mbps = (bits / duration / (1024 * 1024)).toFixed(2);
        setSysInfo((s) => ({ ...s, upload: `${mbps} Mbps` }));
      } catch {}
    };

    measureSpeed();
    measureUpload();
    const speedInt = setInterval(() => {
      measureSpeed();
      measureUpload();
    }, 60000);
    const timeInt = setInterval(
      () => setSysInfo((s) => ({ ...s, time: new Date().toLocaleTimeString() })),
      1000
    );
    return () => {
      clearInterval(speedInt);
      clearInterval(timeInt);
    };
  }, []);

  return (
    <div className="mock-page reveal" ref={permissionsPageRef} style={{ minHeight: "100vh", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      {/* Fullscreen Confirmation Modal */}
      {showFullscreenModal && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: "rgba(0, 0, 0, 0.5)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 9999
        }}>
          <div style={{
            background: "white",
            borderRadius: 8,
            padding: 32,
            boxShadow: "0 10px 40px rgba(0, 0, 0, 0.2)",
            maxWidth: 400,
            textAlign: "center"
          }}>
            <h3 style={{ marginTop: 0, fontSize: 20, fontWeight: 700, marginBottom: 12 }}>Enter Fullscreen Mode</h3>
            <p style={{ margin: "0 0 24px 0", fontSize: 14, color: "#666", lineHeight: 1.5 }}>
              Your interview will run in fullscreen mode to ensure a secure testing environment. You will be unable to switch windows during the assessment.
            </p>
            <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
              <button
                onClick={cancelFullscreen}
                style={{
                  padding: "10px 24px",
                  fontSize: 14,
                  fontWeight: 600,
                  background: "#f3f4f6",
                  border: "1px solid #d1d5db",
                  borderRadius: 4,
                  cursor: "pointer",
                  transition: "all 0.2s"
                }}
                onMouseEnter={(e) => e.target.style.background = "#e5e7eb"}
                onMouseLeave={(e) => e.target.style.background = "#f3f4f6"}
              >
                Cancel
              </button>
              <button
                onClick={enterFullscreenMode}
                style={{
                  padding: "10px 24px",
                  fontSize: 14,
                  fontWeight: 600,
                  background: "#3b82f6",
                  color: "white",
                  border: "none",
                  borderRadius: 4,
                  cursor: "pointer",
                  transition: "all 0.2s"
                }}
                onMouseEnter={(e) => e.target.style.background = "#2563eb"}
                onMouseLeave={(e) => e.target.style.background = "#3b82f6"}
              >
                Enter Fullscreen
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Fullscreen Blocked Warning Modal */}
      {fullscreenBlocked ? (
        <div className="voice-ai-modal-overlay">
          <div className="voice-ai-modal-card" data-fullscreen-warning tabIndex="-1">
            <div className="voice-ai-modal-eyebrow">Fullscreen Required</div>
            <h2 className="voice-ai-modal-title">
              The system check has been paused because you exited fullscreen mode.
            </h2>
            <p className="voice-ai-modal-copy">
              Stay in fullscreen to continue your system check and permissions verification, or cancel and return home.
            </p>
            <div className="voice-ai-modal-actions">
              <button className="go-back-btn" onClick={cancelFullscreenGuard}>
                Cancel
              </button>
              <button className="mock-btn" onClick={restoreFullscreen}>
                Resume
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {/* No mini navbar on this page per request */}
      {/* overall status banner (only when every permission granted) */}
      {allPermissionsGranted && (
        <div style={{ background: "#e6ffed", padding: 12, textAlign: "center", color: "#065f46", fontWeight: 600, fontSize: 12 }}>
          ✅ Success: Your system is compatible. Please make sure to use the same System & Internet settings for your assessment/interview.
        </div>
      )}

      {/* main two‑column section */}
      <div style={{ display: "flex", flexWrap: "wrap", padding: 16, gap: 16, maxWidth: 1440, margin: "0 auto", width: "100%", alignItems: "stretch", flex: "1 1 auto", minHeight: 0 }}>
        {/* left: system check list */}
        <div style={{ flex: "1 1 420px", minWidth: 320, maxWidth: 640, display: "flex", minHeight: 0 }}>
          <div style={{ background: "white", padding: 18, borderRadius: 6, boxShadow: "0 2px 6px rgba(0,0,0,0.08)", flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
            <h2 style={{ marginTop: 0, fontSize: 18, marginBottom: 16, fontWeight: 700 }}>System Check + Verification Photo</h2>

            <div style={{ display: "flex", flexDirection: "column", gap: 14, flex: 1, justifyContent: "space-evenly", minHeight: 0 }}>
              {/* camera */}
              <div
                style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 14, gap: 12, height: 40 }}
              >
                <span className="perm-item" onClick={requestCamera} style={{cursor:'pointer'}}><CameraIcon className="perm-icon" /> Camera</span>
                <button
                  className={`mock-btn grant-btn ${permissions.camera ? "granted" : deniedPerm.camera ? "denied" : ""}`}
                  disabled={permissions.camera || loadingPerm.camera}
                  onClick={requestCamera}
                  style={{ cursor: loadingPerm.camera ? "wait" : "pointer", fontSize: 12, minWidth: 60, height: 38 }}
                >
                  {loadingPerm.camera ? <span className="spinner" /> : permissions.camera ? "✓" : deniedPerm.camera ? "✕" : "Grant"}
                </button>
              </div>

              {/* microphone */}
              <div
                style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 14, gap: 12, height: 40 }}
              >
                <span className="perm-item" onClick={requestMicrophone} style={{cursor:'pointer'}}><MicIcon className="perm-icon" /> Microphone</span>
                <button
                  className={`mock-btn grant-btn ${permissions.microphone ? "granted" : deniedPerm.microphone ? "denied" : ""}`}
                  disabled={permissions.microphone || loadingPerm.microphone}
                  onClick={requestMicrophone}
                  style={{ cursor: loadingPerm.microphone ? "wait" : "pointer", fontSize: 12, minWidth: 60, height: 38 }}
                >
                  {loadingPerm.microphone ? <span className="spinner" /> : permissions.microphone ? "✓" : deniedPerm.microphone ? "✕" : "Grant"}
                </button>
              </div>
              {permissions.microphone && (
                <div style={{ marginTop: 8 }}>
                  <div className="audio-meter-container">
                    <div className="audio-meter">
                      {[...Array(10)].map((_, idx) => {
                        const thresholdDb = -30 + idx * ((-6 + 30) / 10);
                        const segColor = getAudioColor(thresholdDb);
                        return (
                          <div
                            key={idx}
                            className="audio-segment"
                            style={{ background: audioDb >= thresholdDb ? segColor : "#e5e7eb" }}
                          />
                        );
                      })}
                    </div>
                    <span className="audio-db-label">{audioDb.toFixed(1)} dB</span>
                  </div>
                </div>
              )}

              {/* browser */}
              <div
                style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 14, gap: 12, height: 40 }}
              >
                <span className="perm-item" onClick={detectBrowser} style={{cursor:'pointer'}}><BrowserIcon className="perm-icon" /> Browser</span>
                <button
                  className={`mock-btn grant-btn ${permissions.browser ? "granted" : deniedPerm.browser ? "denied" : ""}`}
                  disabled={permissions.browser || loadingPerm.browser}
                  onClick={detectBrowser}
                  style={{ cursor: loadingPerm.browser ? "wait" : "pointer", fontSize: 12, minWidth: 60, height: 38 }}
                >
                  {loadingPerm.browser ? <span className="spinner" /> : permissions.browser ? "✓" : deniedPerm.browser ? "✕" : "Check"}
                </button>
              </div>

              {/* fullscreen */}
              <div
                style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 14, gap: 12, height: 40 }}
              >
                <span className="perm-item" onClick={requestFullscreen} style={{cursor:'pointer'}}><FullscreenIcon className="perm-icon" /> Fullscreen</span>
                <button
                  className={`mock-btn grant-btn ${permissions.fullscreen ? "granted" : deniedPerm.fullscreen ? "denied" : ""}`}
                  disabled={permissions.fullscreen || loadingPerm.fullscreen}
                  onClick={requestFullscreen}
                  style={{ cursor: loadingPerm.fullscreen ? "wait" : "pointer", fontSize: 12, minWidth: 60, height: 38 }}
                >
                  {loadingPerm.fullscreen ? <span className="spinner" /> : permissions.fullscreen ? "✓" : deniedPerm.fullscreen ? "✕" : "Grant"}
                </button>
              </div>

            </div>
          </div>
        </div>

        {/* right: video feed and info panels */}
        <div style={{ flex: "1 1 420px", minWidth: 320, display: "flex", flexDirection: "column", gap: 14, minHeight: 0 }}>
          <div style={{ background: "white", padding: 8, borderRadius: 6, boxShadow: "0 2px 6px rgba(0,0,0,0.08)", flex: "1 1 0", minHeight: 260 }}>
            <video
              ref={videoRef}
              style={{ width: "100%", borderRadius: 4, display: "block", height: "100%" }}
              autoPlay
              playsInline
              muted
            />
          </div>

          <div style={{ background: "white", padding: 16, borderRadius: 6, boxShadow: "0 2px 6px rgba(0,0,0,0.08)", flex: "0 0 auto" }}>
            <h4 style={{ marginTop: 0, fontSize: 14, marginBottom: 10, fontWeight: 700 }}>System Info</h4>
            <div style={{ fontSize: 12, lineHeight: 1.45 }}>
              <div><strong>OS :</strong> {sysInfo.os}</div>
              <div><strong>Dimension :</strong> {sysInfo.dimension}</div>
              <div><strong>Browser :</strong> {sysInfo.browser}</div>
              <div><strong>Cookies :</strong> {sysInfo.cookies}</div>
              <div><strong>Time :</strong> {sysInfo.time}</div>
            </div>
          </div>

          <div style={{ background: "white", padding: 16, borderRadius: 6, boxShadow: "0 2px 6px rgba(0,0,0,0.08)", flex: "0 0 auto" }}>
            <h4 style={{ marginTop: 0, fontSize: 14, marginBottom: 10, fontWeight: 700 }}>Internet Bandwidth</h4>
            <div style={{ fontSize: 12, lineHeight: 1.45 }}>
              <div><strong>Download speed :</strong> {sysInfo.download}</div>
              <div><strong>Upload speed :</strong> {sysInfo.upload}</div>
            </div>
          </div>
        </div>
      </div>

      {/* footer buttons */}
      <div style={{ flex: "0 0 auto", marginTop: 0, textAlign: "center", display: "flex", justifyContent: "center", gap: 12, padding: "0 12px 16px" }}>
        <button className="go-back-btn" onClick={goHome} style={{ padding: "8px 16px", fontSize: 12 }}>🏠 Home</button>
        <button className="go-back-btn" onClick={goBack} style={{ padding: "8px 16px", fontSize: 12 }}>← Back</button>
        <button className="mock-btn footer-btn" onClick={goProceed} disabled={!allPermissionsGranted} style={{ padding: "10px 20px", fontSize: 12 }}>
          Proceed
        </button>
      </div>

    </div>
  );
}

export default Permissions;
