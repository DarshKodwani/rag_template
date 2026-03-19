import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./App.css";
import { LandingPage } from "./components/LandingPage";
import { ChatPanel } from "./components/ChatPanel";
import { DocumentsPage } from "./components/DocumentsPage";

function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <header className="app-header">
          <div className="header-brand">
            <img src="/bil-logo.svg" alt="BIL" className="header-logo" />
            <span className="header-divider" />
            <h1>AnaGuide</h1>
          </div>
          <span className="app-subtitle">Your AnaCredit regulation assistant</span>
        </header>
        <main className="app-main">
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/chat" element={<ChatPanel />} />
            <Route path="/documents" element={<DocumentsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
