import { useState, useRef, useEffect } from 'react'
import { enviarMensagemApi } from '../services/chat'

export function useChat() {
  const [mensagens, setMensagens] = useState([
    {
      id: 1,
      remetente: 'agente',
      texto:
        'Olá! Sou o assistente multiagentes com auto-aprendizado. Como posso ajudar?',
    },
  ])
  const [carregando, setCarregando] = useState(false)
  const chatEndRef = useRef(null)

  const rolarParaFim = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    rolarParaFim()
  }, [mensagens, carregando])

  const enviarMensagem = async (textoInput) => {
    if (!textoInput.trim() || carregando) return

    const mensagemUsuario = {
      id: Date.now(),
      remetente: 'usuario',
      texto: textoInput,
    }

    setMensagens((prev) => [...prev, mensagemUsuario])
    setCarregando(true)

    // Monta o histórico para o backend (últimas 10 mensagens, sem a de boas-vindas)
    const historico = mensagens
      .filter((m) => m.id !== 1)
      .slice(-10)
      .map((m) => ({
        role: m.remetente === 'usuario' ? 'user' : 'assistant',
        content: m.texto,
      }))

    try {
      const data = await enviarMensagemApi(textoInput, historico)

      const mensagemAgente = {
        id: Date.now() + 1,
        remetente: 'agente',
        texto: data.resposta || 'Sem resposta do servidor.',
      }

      setMensagens((prev) => [...prev, mensagemAgente])
    } catch (error) {
      setMensagens((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          remetente: 'agente',
          texto: 'Erro ao conectar com a API do backend.',
          erro: true,
        },
      ])
    } finally {
      setCarregando(false)
    }
  }

  return {
    mensagens,
    carregando,
    chatEndRef,
    enviarMensagem,
  }
}
