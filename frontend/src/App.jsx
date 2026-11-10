import { Header } from './components/Header';
import { MessageList } from './components/MessageList';
import { MessageInput } from './components/MessageInput';
import { useChat } from './hooks/useChat';
import './App.css';

export default function App() {
  const { mensagens, carregando, chatEndRef, enviarMensagem } = useChat();

  return (
    <div className="chat-container">
      <Header />
      <MessageList
        mensagens={mensagens}
        carregando={carregando}
        chatEndRef={chatEndRef}
      />
      <MessageInput
        onEnviar={enviarMensagem}
        desabilitado={carregando}
      />
    </div>
  );
}