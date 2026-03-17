import "./App.css";
import { ChatPanel } from "./components/ChatPanel";
import { UploadPanel } from "./components/UploadPanel";

function App() {
  return (
    <div className="app-layout">
      <header className="app-header">
        <h1>📄 RAG Demo</h1>
        <span className="app-subtitle">RAG · Qdrant · FastAPI</span>
      </header>
      <main className="app-main">
        <aside className="sidebar">
          <UploadPanel />
        </aside>
        <section className="chat-section">
          <ChatPanel />
        </section>
      </main>
    </div>
  );
}

export default App;
