import { useState } from 'react';
import { Send } from 'lucide-react';

export function MessageInput({ onEnviar, desabilitado }) {
  const [texto, setTexto] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!texto.trim() || desabilitado) return;
    onEnviar(texto);
    setTexto('');
  };

  return (
    <footer className="chat-footer">
      <form onSubmit={handleSubmit} className="chat-form">
        <input
          type="text"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="Pergunte algo ao sistema..."
          disabled={desabilitado}
          className="chat-input"
        />
        <button
          type="submit"
          disabled={desabilitado || !texto.trim()}
          className="send-button"
        >
          <Send size={18} />
        </button>
      </form>
    </footer>
  );
}