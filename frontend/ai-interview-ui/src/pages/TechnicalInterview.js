import React from "react";
import { useNavigate } from "react-router-dom";
import "../App.css";
import { useScrollToTop } from "../hooks/useScrollToTop";
import MiniNavbar from "../components/MiniNavbar";

import techImg from "../assets/tech.png";
import mistakeImg from "../assets/mistake.png";

function TechnicalInterview() {
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
      <div className="mock-hero tech-hero">
        <div>
          <h1>Technical Interview</h1>
          <p>
            Prepare for coding rounds, algorithms, system design, and core CS
            concepts with AI guidance.
          </p>

          <button
            className="mock-btn"
            onClick={() => navigate("/topics/technical")}
          >
            Start Technical Mock Interview
          </button>
        </div>

        <img
          src={techImg}
          alt="Technical Interview"
          className="mock-hero-img"
        />
      </div>

      {/* ✅ INTERVIEW MODES SECTION */}
      <div className="mock-section">
        {/* ✅ Header Row Like HR */}
        <div className="section-header-row">
          <h2 className="section-title">Interview Modes</h2>

          <button
            className="small-start-btn"
            onClick={() => navigate("/topics/technical")}
            style={{ display: "none" }}
          >
            Start Technical Mock Interview
          </button>
        </div>

        {/* ✅ CONSOLIDATED CONTENT SECTIONS */}
        <div style={{ marginTop: '30px' }}>
          <div className="aptitude-info-grid">
            <div className="aptitude-info-card aptitude-info-card-learn">
              <div className="aptitude-info-card-tag aptitude-info-card-tag-warm">What you'll learn</div>
              <ul>
                <li>Core computer science fundamentals and theoretical knowledge</li>
                <li>Problem-solving techniques and efficient coding practices</li>
                <li>Designing scalable and robust software systems</li>
              </ul>
            </div>

            <div className="aptitude-info-card aptitude-info-card-types">
              <div className="aptitude-info-card-tag aptitude-info-card-tag-strong">Question types</div>
              <ul>
                <li>DBMS queries, OS concepts, Network protocols, OOPS principles, Data structures basics</li>
                <li>Array/string algorithms, Tree/graph problems, Dynamic programming, Sorting/searching algorithms</li>
                <li>Designing large-scale applications, Database schema design, API architecture, Caching strategies, Load balancing</li>
              </ul>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'center', marginTop: '22px' }}>
            <button
              className="small-start-btn"
              onClick={() => navigate("/topics/technical")}
            >
              Start Technical Mock Interview
            </button>
          </div>
        </div>
      </div>

      {/* ✅ COMMON MISTAKES BOX */}
      <div className="mistake-box">
        <div>
          <h2>⚠ Common Mistakes</h2>
          <ul>
            <li>Jumping into coding without understanding the problem</li>
            <li>Ignoring edge cases and constraints</li>
            <li>Not explaining your approach clearly</li>
          </ul>
        </div>

        <img
          src={mistakeImg}
          alt="Technical Mistakes Illustration"
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

export default TechnicalInterview;
