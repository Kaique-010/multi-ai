import { Sparkles } from 'lucide-react'

export function Header() {
  return (
    <header className="chat-header">
      <div className="header-icon">
        <Sparkles size={24} />
      </div>
      <div>
        <h1 className="header-title">Multiagentes IA</h1>
        <p className="header-subtitle">RAG Vetorial & Cache Dinâmico</p>
      </div>
    </header>
  )
}
