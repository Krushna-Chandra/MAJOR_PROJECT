import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, BriefcaseBusiness, ShieldCheck, Sparkles } from "lucide-react";
import axios from "axios";
import "../App.css";
import { useScrollToTop } from "../hooks/useScrollToTop";
import interviewrLogo from "../assets/Website Logo.png";
import interviewrWordmark from "../assets/Main Logo 2.png";

const api = axios.create({
  baseURL: process.env.REACT_APP_API_BASE || "http://127.0.0.1:8000"
});

const delay = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));

function Auth() {
  const navigate = useNavigate();
  const [isLogin, setIsLogin] = useState(true);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  // Initialize Google Sign-In
  React.useEffect(() => {
    if (isLogin && window.google) {
      window.google.accounts.id.initialize({
        client_id: process.env.REACT_APP_GOOGLE_CLIENT_ID,
        callback: handleGoogleSuccess
      });
      window.google.accounts.id.renderButton(
        document.getElementById('google-signin-button'),
        { theme: 'outline', size: 'large', width: '100%' }
      );
    }
  }, [isLogin]);

  const authHighlights = [
    {
      icon: BriefcaseBusiness,
      title: "Role-focused practice",
      description: "Prepare for HR, technical, resume, and mock rounds in one place.",
    },
    {
      icon: ShieldCheck,
      title: "Reliable account access",
      description: "Secure sign-in and saved progress help you continue where you left off.",
    },
    {
      icon: Sparkles,
      title: "Actionable AI feedback",
      description: "Get clear suggestions after every session to improve faster.",
    },
  ];

  const clearFields = () => {
    setFirstName("");
    setLastName("");
    setEmail("");
    setPassword("");
    setConfirmPassword("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!email || !password || (!isLogin && (!firstName || !lastName || !confirmPassword))) {
      setError("Please fill all fields");
      return;
    }
    if (!isLogin && password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    setLoading(true);
    const loadingStartedAt = Date.now();
    try {
      let res;
      if (isLogin) {
        res = await api.post("/login", { email, password });
        const remainingDelay = Math.max(0, 700 - (Date.now() - loadingStartedAt));
        if (remainingDelay > 0) {
          await delay(remainingDelay);
        }
        localStorage.setItem("token", res.data.access_token);
        localStorage.setItem("user", JSON.stringify(res.data.user));
        window.dispatchEvent(new Event("authchange"));
        clearFields();
        navigate("/");
      } else {
        res = await api.post("/register", {
          first_name: firstName,
          last_name: lastName,
          email,
          password,
        });
        alert("Registered successfully. Please sign in.");
        clearFields();
        setIsLogin(true);
        setLoading(false);
      }
    } catch (err) {
      const msg = typeof err.response?.data?.detail === "string"
        ? err.response.data.detail
        : err.response?.data?.detail?.[0]?.msg || "Authentication failed";
      setError(msg);
      setLoading(false);
    }
  };

  const handleGoogleSuccess = async (response) => {
    setError(null);
    setLoading(true);
    const loadingStartedAt = Date.now();
    try {
      const res = await api.post("/auth/google-login", {
        token: response.credential
      });
      const remainingDelay = Math.max(0, 700 - (Date.now() - loadingStartedAt));
      if (remainingDelay > 0) {
        await delay(remainingDelay);
      }
      localStorage.setItem("token", res.data.access_token);
      localStorage.setItem("user", JSON.stringify(res.data.user));
      window.dispatchEvent(new Event("authchange"));
      clearFields();
      navigate("/");
    } catch (err) {
      const msg = typeof err.response?.data?.detail === "string"
        ? err.response.data.detail
        : err.response?.data?.detail?.[0]?.msg || "Google sign-in failed";
      setError(msg);
      setLoading(false);
    }
  };

  const handleGoogleError = () => {
    setError("Google sign-in failed. Please try again.");
    setLoading(false);
  };

  return (
    <div className="auth-modern-page">
      <button
        type="button"
        className="auth-modern-back"
        onClick={() => navigate("/")}
        aria-label="Back to home"
      >
        <ArrowLeft size={18} />
      </button>
      <div className="auth-modern-layout">
        <section className="auth-modern-showcase">
          <div className="auth-modern-badge">INTERVIEWR</div>
          <div className="auth-modern-brand">
            <div className="auth-modern-logo-lockup">
              <div className="auth-modern-logo-wrap">
                <img src={interviewrLogo} alt="INTERVIEWR" className="auth-modern-logo" />
              </div>
              <img
                src={interviewrWordmark}
                alt="INTERVIEWR wordmark"
                className="auth-modern-wordmark"
              />
            </div>
            <div className="auth-modern-copy">
              <h1>Practice smarter with a cleaner interview workflow.</h1>
              <p>
                A focused platform for mock interviews, resume-based sessions, and AI feedback that helps candidates improve with clarity.
              </p>
            </div>
          </div>

          <div className="auth-modern-highlight-list">
            {authHighlights.map((item) => {
              const Icon = item.icon;
              return (
                <article key={item.title} className="auth-modern-highlight-card">
                  <div className="auth-modern-highlight-icon">
                    <Icon size={20} />
                  </div>
                  <div>
                    <h3>{item.title}</h3>
                    <p>{item.description}</p>
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        <section className="auth-modern-form-shell">
          <div className="auth-modern-form-card">
            <div className="auth-modern-tabbar" role="tablist" aria-label="Authentication mode">
              <span
                className={`auth-modern-tab-indicator ${isLogin ? "is-login" : "is-register"}`}
                aria-hidden="true"
              />
              <button
                type="button"
                className={`auth-modern-tab ${isLogin ? "is-active" : ""}`}
                onClick={() => {
                  clearFields();
                  setError(null);
                  setIsLogin(true);
                }}
              >
                Sign In
              </button>
              <button
                type="button"
                className={`auth-modern-tab ${!isLogin ? "is-active" : ""}`}
                onClick={() => {
                  clearFields();
                  setError(null);
                  setIsLogin(false);
                }}
              >
                Register
              </button>
            </div>

            <div
              key={isLogin ? "sign-in" : "register"}
              className={`auth-modern-panel-motion ${isLogin ? "is-login" : "is-register"}`}
            >
              <div className="auth-modern-form-head">
                <h2 className="auth-modern-title">
                  {isLogin ? "Welcome back" : "Create your account"}
                </h2>
                <p className="auth-modern-subtitle">
                  {isLogin
                    ? "Sign in to continue your interview preparation journey."
                    : "Join INTERVIEWR and start practicing with guided AI interview sessions."}
                </p>
              </div>

              {error && <div className="auth-modern-error">{error}</div>}

              <form onSubmit={handleSubmit} className="auth-modern-form">
                {!isLogin && (
                  <div className="auth-modern-grid">
                    <div className="auth-modern-field">
                      <label className="auth-modern-label">First Name</label>
                      <input
                        type="text"
                        placeholder="John"
                        value={firstName}
                        onChange={(e) => setFirstName(e.target.value)}
                        className="auth-modern-input"
                      />
                    </div>
                    <div className="auth-modern-field">
                      <label className="auth-modern-label">Last Name</label>
                      <input
                        type="text"
                        placeholder="Doe"
                        value={lastName}
                        onChange={(e) => setLastName(e.target.value)}
                        className="auth-modern-input"
                      />
                    </div>
                  </div>
                )}

                <div className="auth-modern-field">
                  <label className="auth-modern-label">Email Address</label>
                  <input
                    type="email"
                    placeholder="name@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="auth-modern-input"
                  />
                </div>

                <div className="auth-modern-field auth-modern-password-field">
                  <label className="auth-modern-label">Password</label>
                  <input
                    type={showPassword ? "text" : "password"}
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="auth-modern-input"
                  />
                  <button
                    type="button"
                    className="auth-modern-eye"
                    onClick={() => setShowPassword((prev) => !prev)}
                  >
                    {showPassword ? "Hide" : "Show"}
                  </button>
                </div>

                {isLogin && (
                  <div className="auth-modern-forgot">
                    <button
                      type="button"
                      className="auth-modern-inline-link"
                      onClick={() => navigate("/forgot-password")}
                    >
                      Forgot password?
                    </button>
                  </div>
                )}

                {!isLogin && (
                  <>
                    <div className="auth-modern-field auth-modern-password-field">
                      <label className="auth-modern-label">Confirm Password</label>
                      <input
                        type={showConfirm ? "text" : "password"}
                        placeholder="Confirm your password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        className="auth-modern-input"
                      />
                      <button
                        type="button"
                        className="auth-modern-eye"
                        onClick={() => setShowConfirm((prev) => !prev)}
                      >
                        {showConfirm ? "Hide" : "Show"}
                      </button>
                    </div>

                    <label className="auth-modern-checkrow">
                      <input type="checkbox" required className="auth-modern-checkbox" />
                      <span>
                        I agree to the <button type="button" className="auth-modern-inline-link">Terms & Conditions</button>
                      </span>
                    </label>
                  </>
                )}

                <button type="submit" disabled={loading} className="auth-modern-submit">
                  {loading ? (
                    <>
                      <span className="auth-btn-spinner" aria-hidden="true" />
                      <span>{isLogin ? "Signing In..." : "Creating Account..."}</span>
                    </>
                  ) : (
                    <>
                      <span>{isLogin ? "Sign In" : "Create Account"}</span>
                      <ArrowRight size={18} />
                    </>
                  )}
                </button>
              </form>

              {isLogin && (
                <div className="auth-modern-divider-section">
                  <div className="auth-modern-divider">
                    <span>OR</span>
                  </div>
                  <div className="auth-modern-google-button" id="google-signin-button"></div>
                </div>
              )}

              <div className="auth-modern-footer">
                <span>
                  {isLogin ? "New to INTERVIEWR?" : "Already have an account?"}
                </span>
                <button
                  type="button"
                  className="auth-modern-switch"
                  onClick={() => {
                    clearFields();
                    setError(null);
                    setIsLogin((prev) => !prev);
                  }}
                >
                  {isLogin ? "Create one" : "Sign in"}
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

export default Auth;
