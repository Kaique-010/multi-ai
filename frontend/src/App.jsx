import { Header } from './components/Header'
import { Sidebar } from './components/SideBar'
import { MessageList } from './components/MessageList'
import { MessageInput } from './components/MessageInput'
import { useChat } from './hooks/useChat'
import './App.css'

export default function App() {
  const {
    mensagens,
    historico,
    carregando,
    carregandoHistorico,
    chatEndRef,
    enviarMensagem,
    carregarHistorico,
  } = useChat()

  return (
    <div className="app-layout">
      <Sidebar
        historico={historico}
        recarregar={carregarHistorico}
        carregando={carregandoHistorico}
      />
      <div className="chat-container">
        <Header />
        <MessageList
          mensagens={mensagens}
          carregando={carregando}
          chatEndRef={chatEndRef}
        />
        <MessageInput onEnviar={enviarMensagem} desabilitado={carregando} />
      </div>
    </div>
  )
}
