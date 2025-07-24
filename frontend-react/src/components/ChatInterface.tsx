import React, { useState, useRef, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useAppStore } from '@/store/useAppStore'
import { apiRequest } from '@/lib/utils'
import { Send, Trash2, MessageSquare, Bot, User } from 'lucide-react'

export const ChatInterface: React.FC = () => {
  const { 
    chatMessages, 
    addChatMessage, 
    updateChatMessage, 
    clearChatMessages,
    selectedModel,
    setSelectedModel 
  } = useAppStore()
  
  const [prompt, setPrompt] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [chatMessages])

  const handleSendMessage = async () => {
    if (!prompt.trim() || isLoading) return

    const currentPrompt = prompt.trim()
    setPrompt('')
    setIsLoading(true)

    // Add message to store
    const messageId = crypto.randomUUID()
    addChatMessage({
      id: messageId,
      prompt: currentPrompt,
      isLoading: true,
    })

    try {
      const response = await apiRequest<{
        ollama_response: string
        webui_response: string
        model: string
        timestamp: number
      }>('/api/chat', {
        method: 'POST',
        body: JSON.stringify({
          prompt: currentPrompt,
          model: selectedModel,
        }),
      })

      updateChatMessage(messageId, {
        ollamaResponse: response.ollama_response,
        webuiResponse: response.webui_response,
        isLoading: false,
      })
    } catch (error) {
      console.error('Chat error:', error)
      updateChatMessage(messageId, {
        ollamaResponse: '❌ Error: Failed to get response from Ollama',
        webuiResponse: '❌ Error: Failed to get response from Open WebUI',
        isLoading: false,
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  return (
    <Card className="col-span-1 lg:col-span-3 h-[600px] flex flex-col">
      <CardHeader className="flex-shrink-0">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-medium flex items-center gap-2">
            <MessageSquare className="h-4 w-4" />
            AI Response Comparison
          </CardTitle>
          <div className="flex items-center gap-2">
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="text-sm border rounded px-2 py-1 bg-background"
            >
              <option value="tinyllama:latest">TinyLlama</option>
              <option value="llama2:latest">Llama 2</option>
              <option value="mistral:latest">Mistral</option>
            </select>
            <Button
              onClick={clearChatMessages}
              variant="outline"
              size="sm"
              disabled={chatMessages.length === 0}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col space-y-4 min-h-0">
        {/* Chat Messages */}
        <div className="flex-1 overflow-auto space-y-4 pr-2">
          {chatMessages.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>Start a conversation to compare AI responses</p>
              <p className="text-xs mt-2">Direct Ollama vs Pipeline-Enhanced Open WebUI</p>
            </div>
          ) : (
            chatMessages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="flex-shrink-0 space-y-2">
          <div className="flex gap-2">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask a question to compare AI responses..."
              className="flex-1 min-h-[60px] px-3 py-2 border rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-primary"
              disabled={isLoading}
            />
            <Button
              onClick={handleSendMessage}
              disabled={!prompt.trim() || isLoading}
              size="lg"
            >
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Press Enter to send, Shift+Enter for new line
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

interface ChatMessageProps {
  message: {
    id: string
    prompt: string
    ollamaResponse?: string
    webuiResponse?: string
    timestamp: Date
    isLoading?: boolean
  }
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  return (
    <div className="space-y-3">
      {/* User Prompt */}
      <div className="chat-message">
        <div className="flex items-start gap-3">
          <User className="h-5 w-5 mt-0.5 text-primary" />
          <div className="flex-1">
            <p className="font-medium text-sm">You</p>
            <p className="text-sm mt-1">{message.prompt}</p>
            <p className="text-xs text-muted-foreground mt-2">
              {message.timestamp.toLocaleTimeString()}
            </p>
          </div>
        </div>
      </div>

      {/* AI Responses */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Ollama Response */}
        <div className="chat-response">
          <div className="flex items-start gap-3">
            <Bot className="h-5 w-5 mt-0.5 text-blue-500" />
            <div className="flex-1">
              <p className="font-medium text-sm mb-2">Direct Ollama</p>
              {message.isLoading ? (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  Generating response...
                </div>
              ) : (
                <p className="text-sm whitespace-pre-wrap">
                  {message.ollamaResponse || 'No response received'}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Open WebUI Response */}
        <div className="chat-response">
          <div className="flex items-start gap-3">
            <Bot className="h-5 w-5 mt-0.5 text-green-500" />
            <div className="flex-1">
              <p className="font-medium text-sm mb-2">Pipeline-Enhanced WebUI</p>
              {message.isLoading ? (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  Generating response...
                </div>
              ) : (
                <p className="text-sm whitespace-pre-wrap">
                  {message.webuiResponse || 'No response received'}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}