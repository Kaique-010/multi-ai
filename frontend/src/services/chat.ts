const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

export interface MensagemHistorico {
  role: 'user' | 'assistant'
  content: string
}

/**
 * Envia uma mensagem para o agente no backend.
 * @param {string} mensagem - Texto digitado pelo usuário.
 * @param {MensagemHistorico[]} historico - Histórico da conversa.
 * @returns {Promise<{resposta: string}>}
 */
export async function enviarMensagemApi(
  mensagem: string,
  historico: MensagemHistorico[] = [],
) {
  const response = await fetch(`${API_URL}/api/chat/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ mensagem, historico }),
  })

  if (!response.ok) {
    throw new Error(`Erro na API (${response.status}): ${response.statusText}`)
  }

  return await response.json()
}

export async function buscarHistoricoApi() {
  const response = await fetch(`${API_URL}/api/chat/historico`)

  if (!response.ok) {
    throw new Error(`Erro na API (${response.status}): ${response.statusText}`)
  }

  return await response.json()
}
