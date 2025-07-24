import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { useAppStore } from '../store/useAppStore'
// Inline apiRequest to avoid module resolution issues
async function apiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = process.env.NODE_ENV === 'development' ? 'http://localhost:8080' : '';
  const response = await fetch(`${baseUrl}${endpoint}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}
import { AlertTriangle, Shield, Zap, Info } from 'lucide-react'

export const DemoControls: React.FC = () => {
  const { demoState, setAvailabilityDemo, setDataLeakDemo } = useAppStore()
  const [isLoading, setIsLoading] = useState({ availability: false, dataLeak: false })
  const [statusMessage, setStatusMessage] = useState<string | null>(null)

  const handleAvailabilityDemo = async () => {
    setIsLoading(prev => ({ ...prev, availability: true }))
    setStatusMessage(null)

    try {
      const response = await apiRequest<{
        message: string
        status: string
        service_failure_active: boolean
        timestamp: number
      }>('/api/availability-demo/toggle', {
        method: 'POST',
      })

      setAvailabilityDemo(response.service_failure_active, response.message)
      setStatusMessage(response.message)
      
      // Clear status message after 5 seconds
      setTimeout(() => setStatusMessage(null), 5000)
    } catch (error) {
      console.error('Availability demo error:', error)
      setStatusMessage('❌ Failed to toggle availability demo')
      setTimeout(() => setStatusMessage(null), 5000)
    } finally {
      setIsLoading(prev => ({ ...prev, availability: false }))
    }
  }

  const handleDataLeakDemo = async () => {
    setIsLoading(prev => ({ ...prev, dataLeak: true }))
    setStatusMessage(null)

    try {
      const response = await apiRequest<{
        message: string
        status: string
        data_types: string[]
        timestamp: number
      }>('/api/data-leak-demo', {
        method: 'POST',
      })

      setDataLeakDemo(true)
      setStatusMessage(response.message)
      
      // Auto-reset data leak demo state after 3 seconds
      setTimeout(() => {
        setDataLeakDemo(false)
        setStatusMessage(null)
      }, 3000)
    } catch (error) {
      console.error('Data leak demo error:', error)
      setStatusMessage('❌ Failed to execute data leak demo')
      setTimeout(() => setStatusMessage(null), 5000)
    } finally {
      setIsLoading(prev => ({ ...prev, dataLeak: false }))
    }
  }

  return (
    <Card className="col-span-1">
      <CardHeader>
        <CardTitle className="text-base font-medium flex items-center gap-2">
          <Shield className="h-4 w-4" />
          Security Demos
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Availability Demo */}
        <div className="space-y-2">
          <Button
            onClick={handleAvailabilityDemo}
            disabled={isLoading.availability}
            variant={demoState.availability.isActive ? 'demo-active' : 'demo'}
            className="w-full"
          >
            {isLoading.availability ? (
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Processing...
              </div>
            ) : (
              <div className="flex items-center gap-2">
                {demoState.availability.isActive ? (
                  <>
                    <AlertTriangle className="h-4 w-4" />
                    🔴 Availability Demo: ON
                  </>
                ) : (
                  <>
                    <Zap className="h-4 w-4" />
                    🟢 Availability Demo: OFF
                  </>
                )}
              </div>
            )}
          </Button>
          
          <div className="text-xs text-muted-foreground space-y-1">
            <p>• Manipulates ConfigMap to simulate service failures</p>
            <p>• Creates HTTP 500 errors for SUSE Observability monitoring</p>
            {demoState.availability.isActive && demoState.availability.configValue && (
              <div className="p-2 bg-muted rounded text-xs">
                <strong>ConfigMap Value:</strong> <code>{demoState.availability.configValue}</code>
              </div>
            )}
          </div>
        </div>

        {/* Data Leak Demo */}
        <div className="space-y-2">
          <Button
            onClick={handleDataLeakDemo}
            disabled={isLoading.dataLeak}
            variant={demoState.dataLeak.isActive ? 'demo-active' : 'secondary'}
            className="w-full"
          >
            {isLoading.dataLeak ? (
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                Sending Data...
              </div>
            ) : (
              <div className="flex items-center gap-2">
                {demoState.dataLeak.isActive ? (
                  <>
                    <AlertTriangle className="h-4 w-4" />
                    🔥 Data Leak Demo (Active)
                  </>
                ) : (
                  <>
                    <Shield className="h-4 w-4" />
                    🔒 Data Leak Demo
                  </>
                )}
              </div>
            )}
          </Button>
          
          <div className="text-xs text-muted-foreground space-y-1">
            <p>• Sends credit card and SSN patterns to external endpoints</p>
            <p>• Triggers NeuVector DLP (Data Loss Prevention) detection</p>
            <p>• Generates observable security alerts</p>
          </div>
        </div>

        {/* Status Message */}
        {statusMessage && (
          <div className="p-3 rounded-lg bg-muted border-l-4 border-primary animate-fade-in">
            <div className="flex items-start gap-2">
              <Info className="h-4 w-4 mt-0.5 text-primary" />
              <div className="text-sm" dangerouslySetInnerHTML={{ __html: statusMessage }} />
            </div>
          </div>
        )}

        {/* Demo Help */}
        <div className="pt-2 border-t">
          <details className="text-xs text-muted-foreground">
            <summary className="cursor-pointer hover:text-foreground transition-colors">
              External kubectl Commands
            </summary>
            <div className="mt-2 space-y-2 font-mono text-xs bg-muted p-2 rounded">
              <div>
                <p className="font-sans font-medium mb-1">Break the app:</p>
                <code className="block">kubectl patch configmap &lt;release&gt;-demo-config -n &lt;namespace&gt; --type=json -p='[{`{"op": "remove", "path": "/data/models-latest"}`}, {`{"op": "add", "path": "/data/models_latest", "value": "broken-model:invalid"}`}]'</code>
              </div>
              <div>
                <p className="font-sans font-medium mb-1">Fix the app:</p>
                <code className="block">kubectl patch configmap &lt;release&gt;-demo-config -n &lt;namespace&gt; --type=json -p='[{`{"op": "remove", "path": "/data/models_latest"}`}, {`{"op": "add", "path": "/data/models-latest", "value": "tinyllama:latest,llama2:latest"}`}]'</code>
              </div>
            </div>
          </details>
        </div>
      </CardContent>
    </Card>
  )
}