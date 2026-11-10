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

    try {
      const data = await enviarMensagemApi(textoInput)

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
