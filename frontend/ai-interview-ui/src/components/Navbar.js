import React, { useEffect, useRef, useState } from "react";
import ImageCropModal from "./ImageCropModal";
import { Link, useNavigate, useLocation } from "react-router-dom";
import "../App.css";
import logo from "../assets/Website Logo.png";
import axios from "axios";
import { LayoutDashboard, Users, Settings, LogOut } from "lucide-react";


function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const popupRef = useRef(null);
  const [showProfile, setShowProfile] = useState(false);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  // Always use user.profile_image for display, keep in sync with localStorage
  const [cropModalImg, setCropModalImg] = useState(null);

  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("user"));
    } catch {
      return null;
    }
  });

  const closeMobileMenu = () => setMobileOpen(false);
  const toggleMobileMenu = () => setMobileOpen((open) => !open);

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

  const performLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    window.dispatchEvent(new Event("authchange"));
    setUser(null);
    setShowProfile(false);
    setShowLogoutConfirm(false);
    navigate("/");
  };

  const handleLogout = () => {
    setShowLogoutConfirm(true);
  };

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (popupRef.current && !popupRef.current.contains(e.target)) {
        setShowProfile(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    setMobileOpen(false);
    setShowProfile(false);
    setShowLogoutConfirm(false);
  }, [location.pathname]);

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth > 900) {
        setMobileOpen(false);
      }
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <div className="navbar-left">
          <Link to="/" className="navbar-home-link" onClick={closeMobileMenu}>
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
          </Link>
        </div>

        <div className={`navbar-center ${mobileOpen ? "mobile-open" : ""}`}>
          <div className="nav-links">
            <button
              className={`nav-link ${location.pathname === "/" ? "active" : ""}`}
              onClick={() => {
                navigate("/");
                closeMobileMenu();
              }}
            >
              Home
            </button>
            <button
              className={`nav-link ${location.pathname === "/hr-interview" ? "active" : ""}`}
              onClick={() => {
                navigate("/hr-interview");
                closeMobileMenu();
              }}
            >
              Practice
            </button>
            <button
              className={`nav-link ${location.pathname === "/dashboard" ? "active" : ""}`}
              onClick={() => {
                navigate("/dashboard");
                closeMobileMenu();
              }}
            >
              Dashboard
            </button>
            <button
              className={`nav-link ${location.pathname === "/resume-analyzer" ? "active" : ""}`}
              onClick={() => {
                navigate("/resume-analyzer");
                closeMobileMenu();
              }}
            >
              Resume Analyzer
            </button>
            <button
              className={`nav-link ${location.pathname === "/about" ? "active" : ""}`}
              onClick={() => {
                navigate("/about");
                closeMobileMenu();
              }}
            >
              About us
            </button>
          </div>
        </div>

        <div className="nav-right navbar-right">
          {!user ? (
            <button
              type="button"
              className="navbar-auth-btn"
              onClick={() => {
                navigate("/auth");
                closeMobileMenu();
              }}
            >
              Sign In / Sign Up
            </button>
          ) : (
            <div className="profile-area" ref={popupRef}>
              <button
                type="button"
                className="profile-card"
                onClick={() => {
                  closeMobileMenu();
                  setShowLogoutConfirm(false);
                  setShowProfile((prev) => !prev);
                }}
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
              </button>

              {showProfile && (
                <div className="profile-popup pro-popup-ui">
                  <div className="profile-popup-top">
                    <div className="profile-img-edit">
<div
                          className="profile-img-circle"
                          style={{ position: 'relative', cursor: 'pointer' }}
                          title="Edit Photo"
                          onClick={e => {
                            e.stopPropagation();
                            document.getElementById('profile-img-input').click();
                          }}
                        >
                          {user?.profile_image ? (
                            <img src={user.profile_image} alt="Profile" style={{ width: '100%', height: '100%', borderRadius: '50%', objectFit: 'cover' }} />
                          ) : (
                            <span className="profile-img-initial">{userInitial}</span>
                          )}
                          <div className="profile-img-hover-text">Edit</div>
                        <input
                          id="profile-img-input"
                          type="file"
                          accept="image/*"
                          style={{ display: 'none' }}
                          onChange={e => {
                            const file = e.target.files[0];
                            if (file) {
                              const reader = new FileReader();
                              reader.onload = ev => setCropModalImg(ev.target.result);
                              reader.readAsDataURL(file);
                            }
                          }}
                        />

                        {cropModalImg && (
                          <ImageCropModal
                            image={cropModalImg}
                            onClose={() => setCropModalImg(null)}
                            onSave={async (img) => {
                              try {
                                setCropModalImg(null);
                                // Send to backend
                                const token = localStorage.getItem("token");
                                const payload = { profile_image: img };
                                const res = await axios.put(
                                  "http://127.0.0.1:8000/profile",
                                  payload,
                                  {
                                    headers: {
                                      Authorization: "Bearer " + token
                                    }
                                  }
                                );
                                // Update user in localStorage
                                const existingUser = JSON.parse(localStorage.getItem("user"));
                                localStorage.setItem(
                                  "user",
                                  JSON.stringify({
                                    ...existingUser,
                                    ...res.data.user
                                  })
                                );
                                setUser(prev => ({ ...prev, ...res.data.user }));
                              } catch (err) {
                                alert(err.response?.data?.detail || "Profile image update failed");
                              }
                            }}
                          />
                        )}
                      </div>
                    </div>
                    <div className="profile-popup-username">{userDisplayName}</div>
                    <div className="profile-popup-email">{user?.email}</div>
                  </div>
                  <div className="profile-popup-links">
                    <button className="profile-popup-link profile-popup-link-row" onClick={() => navigate('/dashboard')}>
                      <span className="profile-popup-link-icon"><LayoutDashboard size={28} color="#111" style={{marginRight:12}} /></span>
                      <span className="profile-popup-link-text">My Dashboard</span>
                    </button>
                    <button className="profile-popup-link profile-popup-link-row" onClick={() => setShowProfile('interviews')}>
                      <span className="profile-popup-link-icon"><Users size={28} color="#111" style={{marginRight:12}} /></span>
                      <span className="profile-popup-link-text">My Interviews</span>
                    </button>
                    <button className="profile-popup-link profile-popup-link-row" onClick={() => setShowProfile('settings')}>
                      <span className="profile-popup-link-icon"><Settings size={28} color="#111" style={{marginRight:12}} /></span>
                      <span className="profile-popup-link-text">Settings</span>
                    </button>
                  </div>
                  {showProfile === 'interviews' && (
                    <div className="profile-popup-section">
                      <div className="profile-popup-section-title">My Interviews</div>
                      <div className="profile-popup-interviews-list">
                        {/* Placeholder for past interviews */}
                        <div className="profile-popup-interview-item">No interviews found.</div>
                      </div>
                    </div>
                  )}
                  {showProfile === 'settings' && (
                    <div className="profile-popup-section">
                      <div className="profile-popup-section-title">Settings</div>
                      <button className="edit-profile-btn" onClick={() => navigate('/profile')}>
                        Edit Profile
                      </button>
                    </div>
                  )}
                  <button className="logout-btn profile-popup-link-row" onClick={handleLogout}>
                    <span className="profile-popup-link-icon"><LogOut size={28} color="#111" style={{marginRight:12}} /></span>
                    <span className="profile-popup-link-text">Logout</span>
                  </button>

                </div>
              )}

              {showLogoutConfirm && (
                <div className="modal-overlay" onClick={() => setShowLogoutConfirm(false)}>
                  <div className="modal-content logout-confirm-modal" onClick={(e) => e.stopPropagation()}>
                    <button
                      type="button"
                      className="modal-close-btn"
                      onClick={() => setShowLogoutConfirm(false)}
                      aria-label="Close logout confirmation"
                    >
                      ×
                    </button>
                    <div className="logout-confirm-pill">Session control</div>
                    <div className="logout-confirm-header">
                      <div className="logout-confirm-icon">
                        <LogOut size={26} color="#DC2626" />
                      </div>
                      <div className="logout-confirm-heading">
                        <h3>Log out now?</h3>
                        <p className="logout-confirm-subtitle">
                          You're about to end your current session.
                        </p>
                      </div>
                    </div>
                    <div className="logout-confirm-note">
                      <div className="logout-confirm-note-label">What happens next</div>
                      <p className="logout-confirm-body">
                        You will be signed out immediately and redirected to the homepage. You can sign back in anytime.
                      </p>
                    </div>
                    <div className="logout-confirm-actions">
                      <button className="mock-btn logout-confirm-primary" onClick={performLogout}>
                        Yes, logout
                      </button>
                      <button className="mock-btn cancel-btn" onClick={() => setShowLogoutConfirm(false)}>
                        Cancel
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          <button
            className={`navbar-toggle ${mobileOpen ? "open" : ""}`}
            onClick={() => {
              setShowProfile(false);
              toggleMobileMenu();
            }}
            aria-label="Toggle navigation"
            aria-expanded={mobileOpen}
          >
            <span />
            <span />
            <span />
          </button>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
