const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

/**
 * Envia uma mensagem para o agente no backend.
 * @param {string} mensagem - Texto digitado pelo usuário.
 * @returns {Promise<{resposta: string}>}
 */
export async function enviarMensagemApi(mensagem) {
  const response = await fetch(`${API_URL}/api/chat/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ mensagem }),
  })

  if (!response.ok) {
    throw new Error(`Erro na API (${response.status}): ${response.statusText}`)
  }

  return await response.json()
}
