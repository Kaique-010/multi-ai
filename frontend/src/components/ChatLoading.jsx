import { Bot, Loader2 } from 'lucide-react';

export function ChatLoading() {
  return (
    <div className="message-row agente">
      <div className="avatar agente">
        <Bot size={20} />
      </div>
      <div className="message-bubble agente loading-indicator">
        <Loader2 size={20} className="spinner" />
        <span>Processando no grafo de agentes...</span>
      </div>
    </div>
  );
}