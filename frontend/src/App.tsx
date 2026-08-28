import { ChatWindow } from "./components/ChatWindow";

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <span className="brand">🏠 DarGlobal × Wasalt</span>
        <span className="subtitle">AI Real Estate Chatbot</span>
      </header>
      <ChatWindow />
    </div>
  );
}
