import { useEffect, useCallback } from 'react'
import { useAppStore } from '../store/useAppStore'
// Inline utils to avoid module resolution issues
async function apiRequest<T>(endpoint: string, options: RequestInit = {}, retries = 2): Promise<T> {
  const baseUrl = process.env.NODE_ENV === 'development' ? 'http://localhost:8080' : '';
  
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await fetch(`${baseUrl}${endpoint}`, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
      });
      
      if (!response.ok) {
        throw new Error(`API request failed: ${response.status} ${response.statusText}`);
      }
      
      return response.json();
    } catch (error) {
      if (attempt === retries) {
        throw error;
      }
      // Wait before retry (exponential backoff)
      await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
    }
  }
  throw new Error('Max retries exceeded');
}

function debounce<T extends (...args: any[]) => void>(func: T, wait: number): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

export const useProviderStatus = () => {
  const { setProviders, setConnected, setLastUpdate } = useAppStore()

  const fetchProviderStatus = useCallback(async () => {
    try {
      const response = await apiRequest<{
        providers: Record<string, {
          status: string
          response_time: string | number
          country: string
          flag: string
        }>
        timestamp: number
      }>('/api/status')

      // Transform the response to match our store interface
      const transformedProviders = Object.entries(response.providers).reduce(
        (acc, [name, provider]: [string, any]) => {
          acc[name] = {
            name,
            status: provider.status as 'online' | 'offline' | 'warning' | 'unknown',
            responseTime: provider.response_time,
            country: provider.country,
            flag: provider.flag,
          }
          return acc
        },
        {} as Record<string, any>
      )

      setProviders(transformedProviders)
      setConnected(true)
      setLastUpdate(new Date())
    } catch (error) {
      console.error('Failed to fetch provider status:', error)
      setConnected(false)
    }
  }, [setProviders, setConnected, setLastUpdate])

  // Debounced version to prevent too frequent updates
  const debouncedFetch = useCallback(debounce(fetchProviderStatus, 1000), [fetchProviderStatus])

  useEffect(() => {
    // Initial fetch
    fetchProviderStatus()

    // Set up polling every 10 seconds
    const interval = setInterval(debouncedFetch, 10000)

    return () => clearInterval(interval)
  }, [fetchProviderStatus, debouncedFetch])

  return { fetchProviderStatus }
}

export const useLoadSimulatorStatus = () => {
  const { setLoadSimulator } = useAppStore()

  const fetchLoadSimulatorStatus = useCallback(async () => {
    try {
      const response = await apiRequest<{
        status: string
        is_running: boolean
        request_count: number
        last_request?: string
      }>('/api/load-simulator/status')

      setLoadSimulator({
        isRunning: response.is_running,
        status: response.status,
        requestCount: response.request_count,
        lastRequest: response.last_request ? new Date(response.last_request) : undefined,
      })
    } catch (error) {
      console.error('Failed to fetch load simulator status:', error)
      setLoadSimulator({
        status: 'error',
        isRunning: false,
      })
    }
  }, [setLoadSimulator])

  useEffect(() => {
    // Initial fetch
    fetchLoadSimulatorStatus()

    // Set up polling every 15 seconds
    const interval = setInterval(fetchLoadSimulatorStatus, 15000)

    return () => clearInterval(interval)
  }, [fetchLoadSimulatorStatus])

  return { fetchLoadSimulatorStatus }
}

export const useHealth = () => {
  const { setConnected } = useAppStore()

  const checkHealth = useCallback(async () => {
    try {
      const response = await fetch('/health')
      setConnected(response.ok)
      return response.ok
    } catch (error) {
      console.error('Health check failed:', error)
      setConnected(false)
      return false
    }
  }, [setConnected])

  useEffect(() => {
    // Initial health check
    checkHealth()

    // Set up health checks every 30 seconds
    const interval = setInterval(checkHealth, 30000)

    return () => clearInterval(interval)
  }, [checkHealth])

  return { checkHealth }
}

// Hook for real-time demo state updates
export const useDemoState = () => {
  const { setAvailabilityDemo, setDataLeakDemo } = useAppStore()

  const checkDemoState = useCallback(async () => {
    try {
      const response = await apiRequest<{
        availability_demo: {
          is_active: boolean
          config_value?: string
          last_toggled?: string
        }
        data_leak_demo: {
          is_active: boolean
          last_triggered?: string
        }
      }>('/api/demo/status')

      setAvailabilityDemo(
        response.availability_demo.is_active,
        response.availability_demo.config_value
      )
      
      setDataLeakDemo(response.data_leak_demo.is_active)
    } catch (error) {
      console.error('Failed to fetch demo state:', error)
    }
  }, [setAvailabilityDemo, setDataLeakDemo])

  useEffect(() => {
    // Initial fetch
    checkDemoState()

    // Set up polling every 5 seconds for demo state
    const interval = setInterval(checkDemoState, 5000)

    return () => clearInterval(interval)
  }, [checkDemoState])

  return { checkDemoState }
}