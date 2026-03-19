import { useNavigate } from "react-router-dom";

export function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="landing">
      <h2 className="landing-title">What would you like to do?</h2>
      <div className="landing-cards">
        <button className="landing-card" onClick={() => navigate("/chat")}>
          <span className="landing-card-icon">💬</span>
          <span className="landing-card-heading">Ask AnaGuide</span>
          <span className="landing-card-desc">
            Ask questions about AnaCredit regulation and get cited answers
          </span>
        </button>
        <button className="landing-card" onClick={() => navigate("/documents")}>
          <span className="landing-card-icon">📚</span>
          <span className="landing-card-heading">Manage Documents</span>
          <span className="landing-card-desc">
            Upload, index, and manage AnaCredit documentation
          </span>
        </button>
      </div>
    </div>
  );
}
