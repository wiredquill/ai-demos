import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Progress } from './ui/progress'
import { useAppStore } from '../store/useAppStore'
import { formatResponseTime, getStatusColor, getStatusIcon } from '../lib/utils'

export const ProviderStatus: React.FC = () => {
  const { providers, isConnected, lastUpdate } = useAppStore()

  const providerEntries = Object.entries(providers)

  return (
    <Card className="col-span-1 lg:col-span-2">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base font-medium">Provider Status</CardTitle>
        <div className="flex items-center space-x-2">
          <div className={`status-indicator ${isConnected ? 'status-online' : 'status-offline'}`} />
          <span className="text-xs text-muted-foreground">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {providerEntries.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <div className="animate-pulse">Loading provider status...</div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {providerEntries.map(([name, provider]) => (
              <ProviderCard key={name} name={name} provider={provider} />
            ))}
          </div>
        )}
        
        {lastUpdate && (
          <div className="text-xs text-muted-foreground text-center pt-2 border-t">
            Last updated: {lastUpdate.toLocaleTimeString()}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

interface ProviderCardProps {
  name: string
  provider: {
    status: string
    responseTime: string | number
    country: string
    flag: string
  }
}

const ProviderCard: React.FC<ProviderCardProps> = ({ name, provider }) => {
  const statusIcon = getStatusIcon(provider.status)
  const statusColor = getStatusColor(provider.status)
  const responseTime = formatResponseTime(provider.responseTime)
  
  // Convert response time to progress percentage for visual indicator
  const getResponseTimeProgress = (time: string | number): number => {
    if (typeof time === 'string') {
      const match = time.match(/(\d+)/)
      if (!match) return 0
      time = parseInt(match[1])
    }
    
    // Scale: 0-100ms = 100%, 100-500ms = 80-20%, >500ms = 0%
    if (time <= 100) return 100
    if (time <= 500) return Math.max(20, 100 - ((time - 100) / 400) * 80)
    return 10
  }

  const progressValue = getResponseTimeProgress(provider.responseTime)

  return (
    <div className="provider-card">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <span className="text-lg">{statusIcon}</span>
          <span className="text-lg">{provider.flag}</span>
        </div>
        <span className={`text-xs font-medium ${statusColor}`}>
          {provider.status.toUpperCase()}
        </span>
      </div>
      
      <div className="space-y-2">
        <div>
          <h4 className="font-medium text-sm truncate" title={name}>
            {name}
          </h4>
          <p className="text-xs text-muted-foreground">{provider.country}</p>
        </div>
        
        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span>Response Time</span>
            <span className="font-mono">{responseTime}</span>
          </div>
          <Progress value={progressValue} className="h-1" />
        </div>
      </div>
    </div>
  )
}