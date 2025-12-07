interface WebSocketMessage {
  type: string;
  dataset_id: string;
  status: string;
  message?: string;
}

export const useDatasetWebSocket = (datasetId: string) => {
  const status = ref<string>('')
  const message = ref<string>('')
  const isConnected = ref<boolean>(false)
  const socket = ref<WebSocket | null>(null)

  const connect = (): void => {

    if (import.meta.server) {
      return
    }

    try {
      const wsURL = `wss://${window.location.host}/ws/datasets/${datasetId}/`
      socket.value = new WebSocket(wsURL)
      
      socket.value.onopen = (): void => {
        isConnected.value = true
      }
      
      socket.value.onmessage = (event: MessageEvent): void => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data)
          if (data.type === 'status_update') {
            status.value = data.status
            message.value = data.message || ''
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }
      
      socket.value.onclose = (): void => {
        isConnected.value = false
      }
      
      socket.value.onerror = (): void => {
        isConnected.value = false
      }
      
    } catch (error) {
      console.error('Error creating WebSocket:', error)
    }
  }
  
  const disconnect = (): void => {
    if (socket.value) {
      socket.value.close()
      socket.value = null
    }
  }
  
  onMounted(() => {
    setTimeout(connect, 100)
  })
  
  onUnmounted(() => {
    disconnect()
  })
  
  return { 
    status, 
    message, 
    isConnected,
    connect, 
    disconnect 
  }
}