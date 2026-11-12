import { Brain, RefreshCw, MessageSquare } from 'lucide-react'

export function Sidebar({ historico, recarregar, carregando, emSelecionar }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-title">
          <Brain size={20} className="icon-brain" />
          <span>Cérebro (PGVector)</span>
        </div>
        <button
          onClick={recarregar}
          disabled={carregando}
          className="btn-refresh"
          title="Atualizar Memórias">
          <RefreshCw size={16} className={carregando ? 'spinner' : ''} />
        </button>
      </div>

      <div className="sidebar-content">
        <div className="sidebar-count">
          {historico.length}{' '}
          {historico.length === 1
            ? 'conhecimento memorizado'
            : 'conhecimentos memorizados'}
        </div>

        {historico.length === 0 ? (
          <div className="sidebar-empty">
            Nenhum conhecimento gravado no banco ainda.
          </div>
        ) : (
          <ul className="sidebar-list">
            {historico.map((item) => (
              <li
                key={item.id}
                className="sidebar-item"
                onClick={() => emSelecionar && emSelecionar(item)}>
                <MessageSquare size={16} className="item-icon" />
                <div className="item-text">
                  <span className="item-id">#{item.id}</span>
                  <p className="item-pergunta">{item.pergunta}</p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  )
}
