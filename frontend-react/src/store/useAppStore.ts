import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

export interface Provider {
  name: string
  status: 'online' | 'offline' | 'warning' | 'unknown'
  responseTime: string | number
  country: string
  flag: string
}

export interface DemoState {
  availability: {
    isActive: boolean
    configValue?: string
    lastToggled?: Date
  }
  dataLeak: {
    isActive: boolean
    lastTriggered?: Date
  }
}

export interface ChatMessage {
  id: string
  prompt: string
  ollamaResponse?: string
  webuiResponse?: string
  timestamp: Date
  isLoading?: boolean
}

export interface LoadSimulator {
  isRunning: boolean
  status: string
  requestCount: number
  lastRequest?: Date
}

interface AppState {
  // Provider status
  providers: Record<string, Provider>
  setProviders: (providers: Record<string, Provider>) => void
  updateProvider: (name: string, provider: Partial<Provider>) => void

  // Demo states
  demoState: DemoState
  setAvailabilityDemo: (isActive: boolean, configValue?: string) => void
  setDataLeakDemo: (isActive: boolean) => void

  // Chat interface
  chatMessages: ChatMessage[]
  addChatMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => void
  updateChatMessage: (id: string, updates: Partial<ChatMessage>) => void
  clearChatMessages: () => void

  // Load simulator
  loadSimulator: LoadSimulator
  setLoadSimulator: (simulator: Partial<LoadSimulator>) => void

  // UI state
  selectedModel: string
  setSelectedModel: (model: string) => void
  isDarkMode: boolean
  toggleDarkMode: () => void
  isConnected: boolean
  setConnected: (connected: boolean) => void

  // Status polling
  lastUpdate: Date | null
  setLastUpdate: (date: Date) => void
}

export const useAppStore = create<AppState>()(
  devtools(
    (set, get) => ({
      // Provider status
      providers: {},
      setProviders: (providers) => set({ providers }),
      updateProvider: (name, provider) =>
        set((state) => ({
          providers: {
            ...state.providers,
            [name]: { ...state.providers[name], ...provider },
          },
        })),

      // Demo states
      demoState: {
        availability: { isActive: false },
        dataLeak: { isActive: false },
      },
      setAvailabilityDemo: (isActive, configValue) =>
        set((state) => ({
          demoState: {
            ...state.demoState,
            availability: {
              isActive,
              configValue,
              lastToggled: new Date(),
            },
          },
        })),
      setDataLeakDemo: (isActive) =>
        set((state) => ({
          demoState: {
            ...state.demoState,
            dataLeak: {
              isActive,
              lastTriggered: isActive ? new Date() : state.demoState.dataLeak.lastTriggered,
            },
          },
        })),

      // Chat interface
      chatMessages: [],
      addChatMessage: (message) =>
        set((state) => ({
          chatMessages: [
            ...state.chatMessages,
            {
              ...message,
              id: crypto.randomUUID(),
              timestamp: new Date(),
            },
          ],
        })),
      updateChatMessage: (id, updates) =>
        set((state) => ({
          chatMessages: state.chatMessages.map((msg) =>
            msg.id === id ? { ...msg, ...updates } : msg
          ),
        })),
      clearChatMessages: () => set({ chatMessages: [] }),

      // Load simulator
      loadSimulator: {
        isRunning: false,
        status: 'stopped',
        requestCount: 0,
      },
      setLoadSimulator: (simulator) =>
        set((state) => ({
          loadSimulator: { ...state.loadSimulator, ...simulator },
        })),

      // UI state
      selectedModel: 'tinyllama:latest',
      setSelectedModel: (model) => set({ selectedModel: model }),
      isDarkMode: false,
      toggleDarkMode: () => set((state) => ({ isDarkMode: !state.isDarkMode })),
      isConnected: false,
      setConnected: (connected) => set({ isConnected: connected }),

      // Status polling
      lastUpdate: null,
      setLastUpdate: (date) => set({ lastUpdate: date }),
    }),
    {
      name: 'ai-compare-store',
    }
  )
)