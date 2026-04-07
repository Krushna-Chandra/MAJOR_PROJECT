import React from "react";
import { useNavigate } from "react-router-dom";
import {
  BarChart3,
  Brain,
  Github,
  Instagram,
  Layers3,
  Linkedin,
  Mic,
  Rocket,
  Sparkles,
  Target,
  Users,
} from "lucide-react";
import Navbar from "../components/Navbar";
import "../App.css";

const signalCards = [
  {
    icon: Brain,
    title: "Adaptive interview engine",
    description: "The platform shapes questions and guidance around the role, skill focus, and level the candidate chooses.",
  },
  {
    icon: Mic,
    title: "Speaking-first rehearsal",
    description: "Voice practice helps users build delivery, pacing, confidence, and natural response structure.",
  },
  {
    icon: BarChart3,
    title: "Insight after every round",
    description: "Reports turn answers into feedback patterns so improvement is visible and practical.",
  },
];

const processCards = [
  {
    step: "01",
    title: "Set your direction",
    description: "Pick the role, language, topic, or interview mode so the session starts with the right preparation context.",
  },
  {
    step: "02",
    title: "Practice with live rhythm",
    description: "The interview flow is designed to feel active and conversational instead of static and repetitive.",
  },
  {
    step: "03",
    title: "Review the pattern",
    description: "Strengths, missed points, and suggested answers create a clean view of what should improve next.",
  },
];

const developerCards = [
  { id: "01", role: "AI Systems", note: "Prompt design, provider routing, and evaluation logic placeholder." },
  { id: "02", role: "Frontend Experience", note: "Interface motion, interaction quality, and product polish placeholder." },
  { id: "03", role: "Backend Platform", note: "API reliability, persistence, and system foundations placeholder." },
  { id: "04", role: "Product Research", note: "User insight, roadmap direction, and interview-learning strategy placeholder." },
];

const socialIcons = [
  { label: "GitHub", icon: Github },
  { label: "LinkedIn", icon: Linkedin },
  { label: "Instagram", icon: Instagram },
];

function AboutUs() {
  const navigate = useNavigate();

  React.useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.2 }
    );

    document.querySelectorAll(".reveal").forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  return (
    <>
      <Navbar />
      <div className="about-lab-shell about-lab-shell-light">
        <div className="about-lab-aurora about-lab-aurora-one" />
        <div className="about-lab-aurora about-lab-aurora-two" />
        <div className="about-lab-noise" />

        <div className="about-lab-container">
          <section className="about-lab-hero">
            <div className="about-lab-title-wrap" aria-hidden="true">
              <span className="about-lab-title">ABOUT US</span>
            </div>
            <div className="about-lab-copy">
              <span className="about-lab-eyebrow">About APIS</span>
              <h1>An interview-prep studio with motion, intelligence, and feedback that keeps evolving.</h1>
              <p>
                APIS is built to make interview preparation feel alive. Instead of static question lists, we combine AI guidance,
                voice-led flow, structured analysis, and repeatable practice loops inside one focused system.
              </p>

              <div className="about-lab-stat-strip">
                <div className="about-lab-stat">
                  <strong>Voice-led</strong>
                  <span>Practice with a delivery-first interview rhythm.</span>
                </div>
                <div className="about-lab-stat">
                  <strong>AI-backed</strong>
                  <span>Generation, evaluation, and summary work together.</span>
                </div>
                <div className="about-lab-stat">
                  <strong>Improvement loop</strong>
                  <span>Every session feeds the next round of practice.</span>
                </div>
              </div>
            </div>

            <div className="about-lab-visual" aria-hidden="true">
              <div className="about-lab-stage">
                <div className="about-lab-stage-ring about-lab-stage-ring-one" />
                <div className="about-lab-stage-ring about-lab-stage-ring-two" />
                <div className="about-lab-stage-ring about-lab-stage-ring-three" />
                <div className="about-lab-stage-beam" />

                <div className="about-lab-center-core">
                  <span>APIS</span>
                  <strong>Interview clarity</strong>
                </div>

                <div className="about-lab-float-card about-lab-float-card-one">
                  <Mic size={16} />
                  <span>Voice simulation</span>
                </div>
                <div className="about-lab-float-card about-lab-float-card-two">
                  <Brain size={16} />
                  <span>Adaptive AI</span>
                </div>
                <div className="about-lab-float-card about-lab-float-card-three">
                  <BarChart3 size={16} />
                  <span>Live feedback</span>
                </div>
                <div className="about-lab-float-card about-lab-float-card-four">
                  <Target size={16} />
                  <span>Role focus</span>
                </div>
                <div className="about-lab-float-card about-lab-float-card-five">
                  <Sparkles size={16} />
                  <span>Confidence boost</span>
                </div>
                <div className="about-lab-float-card about-lab-float-card-six">
                  <Layers3 size={16} />
                  <span>Smart practice loops</span>
                </div>

                <div className="about-lab-wave-grid">
                  {Array.from({ length: 18 }).map((_, index) => (
                    <span key={index} className="about-lab-wave-bar" style={{ animationDelay: `${index * 0.12}s` }} />
                  ))}
                </div>
              </div>
            </div>
          </section>

          <section className="about-lab-developers">
            <div className="about-lab-developers-copy">
              <span className="about-lab-chip">Developers</span>
              <h2>Developer placeholders in a single animated lineup.</h2>
              <p>
                This section presents the team placeholders as one clean developer row with circular identity markers, hovering
                cards, and social icon placeholders.
              </p>
            </div>

            <div className="about-lab-developers-grid">
              {developerCards.map((developer) => (
                <article key={developer.id} className="about-lab-builder-card">
                  <div className="about-lab-builder-avatar">{developer.id}</div>
                  <h3>{developer.role}</h3>
                  <p>{developer.note}</p>
                  <div className="about-lab-builder-socials" aria-label={`${developer.role} social placeholders`}>
                    {socialIcons.map((item) => {
                      const Icon = item.icon;
                      return (
                        <button
                          key={`${developer.id}-${item.label}`}
                          type="button"
                          className="about-lab-social-button"
                          aria-label={`${item.label} placeholder`}
                        >
                          <Icon size={16} />
                        </button>
                      );
                    })}
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="about-lab-ribbon" aria-label="animated platform ribbon">
            <div className="about-lab-ribbon-track">
              <span>AI interviews</span>
              <span>Voice-led practice</span>
              <span>Role-aware prompts</span>
              <span>Actionable reports</span>
              <span>Structured improvement</span>
              <span>AI interviews</span>
              <span>Voice-led practice</span>
              <span>Role-aware prompts</span>
              <span>Actionable reports</span>
              <span>Structured improvement</span>
            </div>
          </section>

          <section className="about-lab-grid">
            <div className="about-lab-panel about-lab-panel-copy">
              <span className="about-lab-chip">Why it feels different</span>
              <h2>We designed the page like a moving studio wall instead of a normal company layout.</h2>
              <p>
                The About experience now reflects the product idea itself: a preparation space with continuous motion, visual
                feedback, and illustrated systems that suggest progress, conversation, and analysis.
              </p>
              <div className="about-lab-bullets">
                <div><Sparkles size={16} /> Continuous ambient animation instead of static hero art</div>
                <div><Layers3 size={16} /> Illustration-driven blocks instead of only text cards</div>
                <div><Target size={16} /> Content grouped around practice, clarity, and growth</div>
              </div>
            </div>

            <div className="about-lab-panel about-lab-panel-illustration">
              <div className="about-lab-panel-screen">
                <div className="about-lab-panel-screen-top">
                  <span>AI system bot</span>
                  <Brain size={16} />
                </div>
                <div className="about-lab-bot-illustration" aria-hidden="true">
                  <div className="about-lab-bot-orb about-lab-bot-orb-one" />
                  <div className="about-lab-bot-orb about-lab-bot-orb-two" />
                  <div className="about-lab-bot-ring about-lab-bot-ring-one" />
                  <div className="about-lab-bot-ring about-lab-bot-ring-two" />
                  <div className="about-lab-bot-speech about-lab-bot-speech-one">
                    <strong>Voice-led interviews</strong>
                    <span>Practice naturally with an AI interviewer.</span>
                  </div>
                  <div className="about-lab-bot-speech about-lab-bot-speech-two">
                    <strong>Adaptive AI feedback</strong>
                    <span>Get smarter evaluation after every answer.</span>
                  </div>
                  <div className="about-lab-bot-speech about-lab-bot-speech-three">
                    <strong>Reports and growth</strong>
                    <span>Track progress through reports and dashboard insights.</span>
                  </div>
                  <div className="about-lab-bot-body">
                    <div className="about-lab-bot-head">
                      <div className="about-lab-bot-antenna" />
                      <div className="about-lab-bot-face">
                        <span className="about-lab-bot-eye" />
                        <span className="about-lab-bot-eye" />
                      </div>
                      <div className="about-lab-bot-mouth" />
                    </div>
                    <div className="about-lab-bot-chest">
                      <Brain size={34} />
                    </div>
                    <div className="about-lab-bot-arm about-lab-bot-arm-left" />
                    <div className="about-lab-bot-arm about-lab-bot-arm-right" />
                    <div className="about-lab-bot-leg about-lab-bot-leg-left" />
                    <div className="about-lab-bot-leg about-lab-bot-leg-right" />
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="about-lab-signal-grid">
            {signalCards.map((card) => {
              const Icon = card.icon;
              return (
                <article key={card.title} className="about-lab-signal-card">
                  <div className="about-lab-signal-icon">
                    <Icon size={20} />
                  </div>
                  <h3>{card.title}</h3>
                  <p>{card.description}</p>
                </article>
              );
            })}
          </section>

          <section className="about-lab-process">
            <div className="about-lab-process-header">
              <span className="about-lab-chip">How APIS works</span>
              <h2>The product is built around a continuous cycle: prepare, perform, review, repeat.</h2>
              <p>
                Every part of the experience is designed to create momentum. Users should feel guided before the interview,
                supported during it, and clearer afterward.
              </p>
            </div>

            <div className="about-lab-process-grid">
              {processCards.map((card) => (
                <article key={card.step} className="about-lab-process-card">
                  <strong>{card.step}</strong>
                  <h3>{card.title}</h3>
                  <p>{card.description}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="about-lab-closing">
            <div className="about-lab-closing-copy">
              <span className="about-lab-chip">Vision</span>
              <h2>Interview preparation should feel like a product that moves with the user, not a page they read once.</h2>
              <p>
                APIS is moving toward a preparation experience that feels active, responsive, and motivating. The goal is simple:
                help people practice with more confidence, understand their performance faster, and improve with each session.
              </p>
            </div>
            <div className="about-lab-closing-panel">
              <div><Users size={18} /> Candidate-first design</div>
              <div><Sparkles size={18} /> Continuous product motion</div>
              <div><Rocket size={18} /> Faster learning cycles</div>
            </div>
          </section>

          <div className="mock-section cta-section reveal" style={{ padding: "70px 30px", marginTop: 40 }}>
            <div style={{ maxWidth: 900, margin: "0 auto", textAlign: "center" }}>
              <h2 style={{ margin: 0 }}>Start your AI Interview Journey Today</h2>
              <p style={{ marginTop: 12, fontSize: 18, opacity: 0.9 }}>
                Dive into a real mock interview and get instant AI feedback to sharpen your skills.
              </p>
              <button
                className="mock-btn"
                style={{ marginTop: 24 }}
                onClick={() => navigate("/mock-interview")}
              >
                Start Interview
              </button>
            </div>
          </div>

        </div>

        <footer className="about-lab-footer">
          <span>© 2026 APIS - AI Powered Interview System</span>
        </footer>
      </div>
    </>
  );
}

export default AboutUs;
