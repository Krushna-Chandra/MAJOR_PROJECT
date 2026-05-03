import React from "react";
import { useNavigate } from "react-router-dom";
import "../App.css";
import { useScrollToTop } from "../hooks/useScrollToTop";
import MiniNavbar from "../components/MiniNavbar";

import hrImg from "../assets/hr.png";
import mistakeImg from "../assets/mistake.png";

function HRInterview() {
  useScrollToTop();
  const navigate = useNavigate();

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

  return (
    <div className="mock-page reveal">
      <MiniNavbar />

      {/* ✅ HERO */}
      <div className="mock-hero beh-hero">
        <div>
          <h1>HR & Behavioral Interview</h1>
          <p>
            Practice communication, confidence, personality-based HR questions, teamwork, leadership, and STAR-based behavioral questions with AI feedback.
          </p>
          <button
            className="mock-btn"
            onClick={() => navigate("/topics/hr")}
          >
            Start HR/Behavioral Mock Interview
          </button>
        </div>
        <img src={hrImg} alt="HR Interview" className="mock-hero-img" />
      </div>

      {/* ✅ PRACTICE MODES HEADER ROW */}
      <div className="mock-section">
        <div className="section-header-row" style={{ justifyContent: "flex-end", display: "none" }}>
          <button
            className="small-start-btn"
            onClick={() => navigate("/topics/hr")}
          >
            Start HR Mock Interview
          </button>
        </div>

        {/* ✅ CONSOLIDATED CONTENT SECTIONS */}
        <div style={{ marginTop: '30px' }}>
          <div className="aptitude-info-grid">
            <div className="aptitude-info-card aptitude-info-card-learn">
              <div className="aptitude-info-card-tag aptitude-info-card-tag-warm">What you'll learn</div>
              <ul>
                <li>Basic communication skills and interview etiquette</li>
                <li>Structured answering techniques and company research</li>
                <li>Negotiation skills and handling difficult questions</li>
                <li>Effective communication and conflict resolution in teams</li>
                <li>STAR method (Situation, Task, Action, Result) for structured answers</li>
                <li>Managing stress and maintaining composure under pressure</li>
              </ul>
            </div>

            <div className="aptitude-info-card aptitude-info-card-types">
              <div className="aptitude-info-card-tag aptitude-info-card-tag-strong">Question types</div>
              <ul>
                <li>Tell me about yourself, Why this company, Basic strengths/weaknesses</li>
                <li>Why this role, Company culture fit, Career goals and aspirations</li>
                <li>Salary expectations, Previous failures, Handling criticism, Exit scenarios</li>
                <li>Teamwork examples, Resolving conflicts, Working with difficult colleagues</li>
                <li>Leadership experiences, Problem-solving scenarios, Achievement examples</li>
                <li>High-pressure situations, Meeting deadlines, Crisis management, Work-life balance</li>
              </ul>
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'center', marginTop: '22px' }}>
            <button
              className="small-start-btn"
              onClick={() => navigate("/topics/hr")}
            >
              Start HR Mock Interview
            </button>
          </div>
        </div>
      </div>

      {/* ✅ COMMON MISTAKES BOX */}
      <div className="mistake-box">
        <div>
          <h2>⚠ Common Mistakes</h2>
          <ul>
            <li>Speaking too fast or with unclear pronunciation</li>
            <li>Not preparing specific examples beforehand</li>
            <li>Failing to research the company and role</li>
          </ul>
        </div>

        <img
          src={mistakeImg}
          alt="HR Mistakes Illustration"
          className="mistake-img"
        />
      </div>

      {/* ✅ FOOTER */}
      <div className="bottom-footer">
        Prepared by AI Powered Interview System
      </div>
    </div>
  );
}

export default HRInterview;
