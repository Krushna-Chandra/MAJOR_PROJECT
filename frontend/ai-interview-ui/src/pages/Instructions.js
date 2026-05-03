import React, { useCallback, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import "../App.css";
import { useScrollToTop } from "../hooks/useScrollToTop";
import logo from "../assets/Website Logo.png";
import { useInterviewFullscreenGuard } from "../hooks/useInterviewFullscreenGuard";
import { useRevealFullscreenWarning } from "../hooks/useRevealFullscreenWarning";

function Instructions() {
  useScrollToTop();
  const navigate = useNavigate();
  const location = useLocation();
  const cancelSetup = useCallback(() => {
    navigate("/", { replace: true });
  }, [navigate]);
  const { fullscreenBlocked, restoreFullscreen, cancelFullscreenGuard } =
    useInterviewFullscreenGuard({ onCancel: cancelSetup });
  useRevealFullscreenWarning(fullscreenBlocked);

  const [user] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("user"));
    } catch {
      return null;
    }
  });

  // warn before leaving page when user tries to navigate away
  React.useEffect(() => {
    const handleBeforeUnload = (e) => {
      e.preventDefault();
      e.returnValue = "All submissions and saved data will be lost";
      return "All submissions and saved data will be lost";
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, []);

  const getUserDisplayName = (user) => {
    if (!user) return "User";
    if (user.first_name && user.last_name)
      return `${user.first_name} ${user.last_name}`;
    if (user.first_name) return user.first_name;
    if (user.last_name) return user.last_name;
    if (user.email) return user.email.split("@")[0];
    return "User";
  };

  const userDisplayName = getUserDisplayName(user);
  const userInitial = userDisplayName ? userDisplayName[0].toUpperCase() : "U";
  
  const [agreedToAll, setAgreedToAll] = useState(false);
  const [alertMessage, setAlertMessage] = useState("");

  const handleContinue = () => {
    if (!agreedToAll) {
      setAlertMessage("Please agree to all instructions before proceeding.");
      setTimeout(() => setAlertMessage(""), 3000);
      return;
    }
    navigate("/interview", { state: location.state || {} });
  };

  const handleBack = () => {
    navigate("/permissions", { state: location.state || {} });
  };

  const instructions = [
    { icon: "🤫", title: "Quiet Environment", desc: "Ensure you're in a quiet place with minimal background noise." },
    { icon: "📹", title: "Face the Camera", desc: "Position your device so your face is clearly visible in the frame." },
    { icon: "🚫", title: "Don't Switch Tabs", desc: "Keep the interview window active. Tab-switching will be detected." },
    { icon: "🎤", title: "Check Microphone", desc: "Test your microphone before starting. Audio quality matters." },
    { icon: "⏱️", title: "Time Your Answers", desc: "You'll have a set time for each question. Don't rush or overthink." },
    { icon: "💡", title: "Think Before Speaking", desc: "Take 5-10 seconds to organize your thoughts before answering." }
  ];

  const checklistItems = [
    { icon: "🎙️", text: "Camera and microphone are working properly" },
    { icon: "🖼️", text: "Background is clean and professional" },
    { icon: "☀️", text: "You have good lighting on your face" },
    { icon: "📵", text: "Phone is on silent or away from desk" },
    { icon: "💻", text: "All other applications are closed" },
    { icon: "💧", text: "You have water nearby (optional but helpful)" },
    { icon: "🔓", text: "Ready for permission checks (camera, microphone, fullscreen)" }
  ];

  return (
    <div className="instructions-page-new">
      {/* NAVBAR - Same as home but without nav links */}
      <nav className="navbar">
        <div className="navbar-inner">
          <div className="navbar-left">
            <div className="navbar-home-link" style={{ cursor: 'default' }}>
              <img
                src={logo}
                alt="INTERVIEWR Logo"
                className="navbar-logo"
              />
              <div className="navbar-brand">
                <div className="navbar-brand-title">
                  <h2>
                    INTERVIEW
                    <span className="brand-r">R</span>
                  </h2>
                  <span className="navbar-brand-pipe">|</span>
                  <span className="navbar-brand-sub">
                    <span>AI Powered</span>
                    <span>Interview System</span>
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Empty center - no nav links */}
          <div className="navbar-center"></div>

          {/* Profile only - not clickable */}
          <div className="nav-right navbar-right">
            {user && (
              <div className="profile-area">
                <div
                  className="profile-card"
                  style={{ cursor: 'default' }}
                >
                  <div className="profile-icon">
                    {user?.profile_image ? (
                      <img src={user.profile_image} alt="Profile" style={{ width: '100%', height: '100%', borderRadius: '50%', objectFit: 'cover' }} />
                    ) : (
                      userInitial
                    )}
                  </div>

                  <div className="profile-user-details">
                    <span className="profile-user-name">{userDisplayName}</span>
                    <span className="profile-user-email">{user?.email}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* PAGE CONTENT - NEW UI */}
      <div className="instructions-content-new">
        <div className="instructions-wrapper">
          {/* Header Section */}
          <div className="instructions-header-new">
            <h1>Interview Instructions</h1>
            <p>Please review these guidelines before starting your interview</p>
          </div>

          {/* Instructions Grid */}
          <div className="instructions-grid-new">
            {instructions.map((item, index) => (
              <div key={index} className="instruction-item-new">
                <div className="instruction-icon-new">{item.icon}</div>
                <h3>{item.title}</h3>
                <p>{item.desc}</p>
              </div>
            ))}
          </div>

          {/* Pre-Interview Checklist as Instruction Cards */}
          <div className="checklist-section-wrapper">
            <div className="instructions-grid-new">
              {checklistItems.map((item, idx) => (
                <div key={idx} className="instruction-item-new">
                  <div className="instruction-icon-new">{item.icon}</div>
                  <p>{item.text}</p>
                </div>
              ))}
            </div>

          </div>

          {/* Agree to All Checkbox */}
          <div className="checklist-agree-all">
            <label htmlFor="agreeToAll">Agree to all</label>
            <input 
              type="checkbox" 
              id="agreeToAll" 
              checked={agreedToAll}
              onChange={(e) => setAgreedToAll(e.target.checked)}
            />
          </div>

          {/* Custom Alert */}
          {alertMessage && (
            <div className="custom-alert-message">
              {alertMessage}
            </div>
          )}

          {/* Action Buttons */}
          <div className="instructions-buttons-new">
            <button
              className="btn-continue-new"
              onClick={handleContinue}
            >
              Let's Begin
            </button>
            <button
              className="btn-back-new"
              onClick={handleBack}
            >
              ← Go Back
            </button>
          </div>

          {/* Footer */}
          <div className="instructions-footer-new">
            Questions? Review our FAQs or contact support
          </div>
        </div>
      </div>
      {fullscreenBlocked ? (
        <div className="voice-ai-modal-overlay">
          <div className="voice-ai-modal-card" data-fullscreen-warning tabIndex="-1">
            <div className="voice-ai-modal-eyebrow">Fullscreen Required</div>
            <h2 className="voice-ai-modal-title">
              The interview setup is paused because fullscreen mode was exited.
            </h2>
            <p className="voice-ai-modal-copy">
              Stay in fullscreen to continue the interview setup, or cancel this interview setup now.
            </p>
            <div className="voice-ai-modal-actions">
              <button className="go-back-btn" onClick={cancelFullscreenGuard}>
                Cancel Interview Setup
              </button>
              <button className="mock-btn" onClick={restoreFullscreen}>
                Stay in Fullscreen
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default Instructions;

