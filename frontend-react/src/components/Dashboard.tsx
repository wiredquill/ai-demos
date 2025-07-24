import React from 'react'
import { ProviderStatus } from './ProviderStatus'
import { DemoControls } from './DemoControls'
import { LoadSimulator } from './LoadSimulator'
import { ChatInterface } from './ChatInterface'
import { useProviderStatus, useLoadSimulatorStatus, useHealth, useDemoState } from '@/hooks/useApi'
import { useAppStore } from '@/store/useAppStore'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Moon, Sun, RefreshCw, Wifi, WifiOff } from 'lucide-react'

export const Dashboard: React.FC = () => {
  const { isDarkMode, toggleDarkMode, isConnected } = useAppStore()
  const { fetchProviderStatus } = useProviderStatus()
  const { fetchLoadSimulatorStatus } = useLoadSimulatorStatus()
  
  // Initialize all API hooks
  useHealth()
  useDemoState()

  const handleRefresh = async () => {
    await Promise.all([
      fetchProviderStatus(),
      fetchLoadSimulatorStatus(),
    ])
  }

  return (
    <div className={`min-h-screen bg-background ${isDarkMode ? 'dark' : ''}`}>
      {/* Header */}
      <header className="border-b bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-suse-primary rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">AI</span>
                </div>
                <div>
                  <h1 className="text-xl font-bold">AI Compare Dashboard</h1>
                  <p className="text-sm text-muted-foreground">
                    Enterprise LLM Comparison & Monitoring
                  </p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              {/* Connection Status */}
              <div className="flex items-center space-x-1 px-3 py-1 rounded-full bg-muted text-sm">
                {isConnected ? (
                  <>
                    <Wifi className="h-3 w-3 text-status-online" />
                    <span className="text-status-online">Connected</span>
                  </>
                ) : (
                  <>
                    <WifiOff className="h-3 w-3 text-status-offline" />
                    <span className="text-status-offline">Disconnected</span>
                  </>
                )}
              </div>
              
              {/* Refresh Button */}
              <Button
                onClick={handleRefresh}
                variant="outline"
                size="sm"
                className="flex items-center gap-2"
              >
                <RefreshCw className="h-4 w-4" />
                Refresh
              </Button>
              
              {/* Dark Mode Toggle */}
              <Button
                onClick={toggleDarkMode}
                variant="outline"
                size="sm"
              >
                {isDarkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6 space-y-6">
        {/* Connection Warning */}
        {!isConnected && (
          <Card className="border-status-offline bg-destructive/10">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 text-destructive">
                <WifiOff className="h-4 w-4" />
                <span className="font-medium">Connection Lost</span>
                <span>- Unable to connect to backend API. Some features may not work.</span>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Top Row - Status and Controls */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Provider Status - Takes 2 columns on large screens */}
          <ProviderStatus />
          
          {/* Demo Controls */}
          <DemoControls />
          
          {/* Load Simulator */}
          <LoadSimulator />
        </div>

        {/* Bottom Row - Chat Interface */}
        <div className="grid grid-cols-1 gap-6">
          <ChatInterface />
        </div>

        {/* Footer Info */}
        <div className="text-center text-sm text-muted-foreground py-4">
          <p>
            SUSE AI Compare Dashboard • Built with React 19 + TypeScript + Tailwind CSS
          </p>
          <p className="mt-1">
            Real-time monitoring for Ollama vs Open WebUI pipeline comparisons
          </p>
        </div>
      </main>
    </div>
  )
}