import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Progress } from './ui/progress'
import { useAppStore } from '../store/useAppStore'
import { apiRequest } from '../lib/utils'
import { Play, Square, BarChart3, Clock } from 'lucide-react'

export const LoadSimulator: React.FC = () => {
  const { loadSimulator, setLoadSimulator } = useAppStore()
  const [isLoading, setIsLoading] = useState(false)

  const handleToggleLoadSimulator = async () => {
    setIsLoading(true)
    
    try {
      if (loadSimulator.isRunning) {
        // Stop load simulator
        const response = await apiRequest<{
          message: string
          status: string
          simulator_status: string
        }>('/api/load-simulator/stop', {
          method: 'POST',
        })
        
        setLoadSimulator({
          isRunning: false,
          status: response.status,
        })
      } else {
        // Start load simulator
        const response = await apiRequest<{
          message: string
          status: string
          simulator_status: string
        }>('/api/load-simulator/start', {
          method: 'POST',
        })
        
        setLoadSimulator({
          isRunning: true,
          status: response.status,
          lastRequest: new Date(),
        })
      }
    } catch (error) {
      console.error('Load simulator error:', error)
      setLoadSimulator({
        status: 'error',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const getStatusProgress = (): number => {
    if (loadSimulator.isRunning) return 100
    if (loadSimulator.status === 'error') return 0
    return 50
  }

  const getStatusColor = (): string => {
    if (loadSimulator.isRunning) return 'text-status-online'
    if (loadSimulator.status === 'error') return 'text-status-offline'
    return 'text-status-warning'
  }

  return (
    <Card className="col-span-1">
      <CardHeader>
        <CardTitle className="text-base font-medium flex items-center gap-2">
          <BarChart3 className="h-4 w-4" />
          Load Simulator
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Status Display */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Status</span>
            <span className={`text-sm font-medium ${getStatusColor()}`}>
              {loadSimulator.isRunning ? '🟢 Running' : 
               loadSimulator.status === 'error' ? '🔴 Error' : '⏹️ Stopped'}
            </span>
          </div>
          
          <Progress value={getStatusProgress()} className="h-2" />
          
          {loadSimulator.requestCount > 0 && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Requests Sent</span>
              <span className="font-mono">{loadSimulator.requestCount}</span>
            </div>
          )}
          
          {loadSimulator.lastRequest && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              Last request: {loadSimulator.lastRequest.toLocaleTimeString()}
            </div>
          )}
        </div>

        {/* Control Button */}
        <Button
          onClick={handleToggleLoadSimulator}
          disabled={isLoading}
          variant={loadSimulator.isRunning ? 'destructive' : 'default'}
          className="w-full"
        >
          {isLoading ? (
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              {loadSimulator.isRunning ? 'Stopping...' : 'Starting...'}
            </div>
          ) : (
            <div className="flex items-center gap-2">
              {loadSimulator.isRunning ? (
                <>
                  <Square className="h-4 w-4" />
                  Stop Load Simulator
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Start Load Simulator
                </>
              )}
            </div>
          )}
        </Button>

        {/* Description */}
        <div className="text-xs text-muted-foreground space-y-1">
          <p>• Generates HTTP traffic for observability monitoring</p>
          <p>• Sends prompts to chat endpoints every 30 seconds</p>
          <p>• Health checks and metrics endpoint testing</p>
          {loadSimulator.isRunning && (
            <div className="p-2 bg-muted rounded">
              <p className="text-status-online">✅ Generating observable HTTP traffic patterns</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}