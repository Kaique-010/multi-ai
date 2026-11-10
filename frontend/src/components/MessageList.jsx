import { Bot, User } from 'lucide-react';
import { ChatLoading } from './ChatLoading';

export function MessageList({ mensagens, carregando, chatEndRef }) {
  return (
    <main className="messages-area">
      {mensagens.map((msg) => (
        <div key={msg.id} className={`message-row ${msg.remetente}`}>
          <div className={`avatar ${msg.remetente}`}>
            {msg.remetente === 'usuario' ? <User size={20} /> : <Bot size={20} />}
          </div>
          <div className={`message-bubble ${msg.remetente} ${msg.erro ? 'erro' : ''}`}>
            {msg.texto}
          </div>
        </div>
      ))}

      {carregando && <ChatLoading />}
      <div ref={chatEndRef} />
    </main>
  );
}