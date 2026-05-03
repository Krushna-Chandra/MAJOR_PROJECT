import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import axios from "axios";
import "../App.css";
import { useScrollToTop } from "../hooks/useScrollToTop";
import interviewrLogo from "../assets/Website Logo.png";
import { Mail, CheckCircle, AlertCircle, Loader } from "lucide-react";

const api = axios.create({
  baseURL: process.env.REACT_APP_API_BASE || "http://127.0.0.1:8000"
});

function VerifyEmail() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState("verifying"); // verifying, success, error, expired
  const [message, setMessage] = useState("");
  const [email, setEmail] = useState("");
  const [resendLoading, setResendLoading] = useState(false);
  const [resendMessage, setResendMessage] = useState("");
  const [resendError, setResendError] = useState("");

  useScrollToTop();

  useEffect(() => {
    const verifyEmailToken = async () => {
      try {
        const token = searchParams.get("token");
        const emailParam = searchParams.get("email");

        if (!token || !emailParam) {
          setStatus("error");
          setMessage("Invalid verification link. Missing token or email.");
          return;
        }

        setEmail(emailParam);

        // Call verify-email endpoint
        const response = await api.post("/verify-email", {
          token,
          email: emailParam
        });

        // Store token and redirect to home
        localStorage.setItem("token", response.data.access_token);
        localStorage.setItem("user", JSON.stringify(response.data.user));
        window.dispatchEvent(new Event("authchange"));

        setStatus("success");
        setMessage("Email verified successfully! Redirecting...");

        // Redirect after 2 seconds
        setTimeout(() => {
          navigate("/");
        }, 2000);
      } catch (err) {
        const errorMsg =
          typeof err.response?.data?.detail === "string"
            ? err.response.data.detail
            : err.response?.data?.detail?.[0]?.msg || "Verification failed";

        if (errorMsg.includes("expired")) {
          setStatus("expired");
        } else {
          setStatus("error");
        }
        setMessage(errorMsg);
      }
    };

    verifyEmailToken();
  }, [searchParams, navigate]);

  const handleResendEmail = async () => {
    try {
      setResendLoading(true);
      setResendError("");
      setResendMessage("");

      const emailParam = searchParams.get("email");
      if (!emailParam) {
        setResendError("Email not found in verification link");
        setResendLoading(false);
        return;
      }

      const response = await api.post("/resend-verification-email", {
        email: emailParam
      });

      setResendMessage("Verification email sent! Check your inbox.");
      setResendLoading(false);
    } catch (err) {
      const errorMsg =
        typeof err.response?.data?.detail === "string"
          ? err.response.data.detail
          : "Failed to resend email";
      setResendError(errorMsg);
      setResendLoading(false);
    }
  };

  return (
    <div className="auth-modern-page">
      <button
        type="button"
        className="auth-modern-back"
        onClick={() => navigate("/")}
        aria-label="Back to home"
      >
        ←
      </button>

      <div className="verify-email-container" style={{ minHeight: "100vh" }}>
        <div className="verify-email-card">
          <div className="verify-email-header">
            <img src={interviewrLogo} alt="Interviewr" className="verify-email-logo" />
          </div>

          {status === "verifying" && (
            <div className="verify-email-content">
              <Loader size={48} className="verify-email-spinner" />
              <h2>Verifying Your Email</h2>
              <p>Please wait while we verify your email address...</p>
            </div>
          )}

          {status === "success" && (
            <div className="verify-email-content success">
              <CheckCircle size={64} className="verify-email-icon success" />
              <h2>Email Verified!</h2>
              <p>{message}</p>
              <p className="verify-email-redirect">Redirecting to dashboard...</p>
            </div>
          )}

          {status === "error" && (
            <div className="verify-email-content error">
              <AlertCircle size={64} className="verify-email-icon error" />
              <h2>Verification Failed</h2>
              <p>{message}</p>
              {status === "expired" && (
                <>
                  <p style={{ marginTop: "20px", fontSize: "14px" }}>
                    Your verification link has expired.
                  </p>
                  <button
                    onClick={handleResendEmail}
                    disabled={resendLoading}
                    className="verify-email-button"
                  >
                    {resendLoading ? "Sending..." : "Resend Verification Email"}
                  </button>
                  {resendMessage && (
                    <p className="verify-email-success-msg">{resendMessage}</p>
                  )}
                  {resendError && (
                    <p className="verify-email-error-msg">{resendError}</p>
                  )}
                </>
              )}
              <div style={{ marginTop: "30px" }}>
                <button
                  onClick={() => navigate("/auth")}
                  className="verify-email-back-button"
                >
                  Back to Login
                </button>
              </div>
            </div>
          )}

          {status === "expired" && (
            <div className="verify-email-content error">
              <AlertCircle size={64} className="verify-email-icon error" />
              <h2>Verification Link Expired</h2>
              <p>Your verification link has expired.</p>
              <button
                onClick={handleResendEmail}
                disabled={resendLoading}
                className="verify-email-button"
              >
                {resendLoading ? "Sending..." : "Request New Verification Email"}
              </button>
              {resendMessage && (
                <p className="verify-email-success-msg">{resendMessage}</p>
              )}
              {resendError && (
                <p className="verify-email-error-msg">{resendError}</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default VerifyEmail;
